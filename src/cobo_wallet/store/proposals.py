from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from web3 import Web3

from cobo_wallet.amounts import format_eth_storage, format_optional_eth_storage
from cobo_wallet.config.env import Settings
from cobo_wallet.models import Proposal
from cobo_wallet.store.common import read_json, write_json


class ProposalStore:
    def __init__(self, settings: Settings) -> None:
        self.path = Path(settings.demo_data_dir) / "proposals.json"
        self.audit_path = Path(settings.demo_data_dir) / "audit.jsonl"
        self.settings = settings

    def _load_confirm_transfer_audit(self) -> dict[str, dict]:
        if not self.audit_path.exists():
            return {}

        records: dict[str, dict] = {}
        with self.audit_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("action") != "wallet_confirm_transfer":
                    continue

                payload = record.get("payload") or {}
                result = payload.get("result") or {}
                proposal_id = payload.get("proposal_id")
                if not proposal_id or not isinstance(result, dict):
                    continue

                records[proposal_id] = {
                    "requested_to": result.get("requested_to"),
                    "recipient_name": result.get("recipient_name"),
                    "tx_hash": result.get("tx_hash"),
                    "estimated_fee_eth": result.get("estimated_fee_eth"),
                    "estimated_total_cost_eth": result.get("estimated_total_cost_eth"),
                    "balance_before_eth": result.get("balance_before_eth"),
                    "balance_after_eth": result.get("balance_after_eth"),
                }
        return records

    def list(self) -> list[Proposal]:
        raw = read_json(self.path, default=[])
        confirm_transfer_audit = self._load_confirm_transfer_audit()
        normalized: list[dict] = []
        changed = False
        removed_fields = {
            "execution_mode",
            "estimated_total_cost_eth",
            "balance_after_eth",
            "explorer_url",
            "execution_message",
        }
        for item in raw:
            normalized_item = dict(item)
            audit_item = confirm_transfer_audit.get(
                normalized_item.get("proposal_id", ""),
                {},
            )
            legacy_total_cost = normalized_item.get("estimated_total_cost_eth")
            legacy_balance_after = normalized_item.get("balance_after_eth")
            if legacy_total_cost is None:
                legacy_total_cost = audit_item.get("estimated_total_cost_eth")
            if legacy_balance_after is None:
                legacy_balance_after = audit_item.get("balance_after_eth")
            if not normalized_item.get("requested_to"):
                normalized_item["requested_to"] = normalized_item.get("to")
                changed = True
            audit_requested_to = audit_item.get("requested_to")
            if (
                audit_requested_to
                and normalized_item.get("requested_to") in {None, normalized_item.get("to")}
                and normalized_item.get("requested_to") != audit_requested_to
            ):
                normalized_item["requested_to"] = audit_requested_to
                changed = True
            audit_recipient_name = audit_item.get("recipient_name")
            if audit_recipient_name and not normalized_item.get("recipient_name"):
                normalized_item["recipient_name"] = audit_recipient_name
                changed = True
            if normalized_item.get("status") == "approved":
                normalized_item["status"] = "authorized"
                changed = True
            if (
                normalized_item.get("status") == "authorized"
                and not normalized_item.get("authorization_token")
            ):
                normalized_item["status"] = "awaiting_local_authorization"
                normalized_item["authorization_expires_at"] = None
                changed = True
            if (
                normalized_item.get("status") == "awaiting_local_authorization"
                and normalized_item.get("user_confirmed_at") is None
            ):
                normalized_item["user_confirmed_at"] = normalized_item.get("created_at")
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("tx_hash")
                and normalized_item.get("executed_at") is None
            ):
                normalized_item["executed_at"] = (
                    normalized_item.get("local_authorized_at")
                    or normalized_item.get("user_confirmed_at")
                    or normalized_item.get("created_at")
                )
                changed = True
            if (
                normalized_item.get("status") == "rejected"
                and normalized_item.get("canceled_at") is None
            ):
                normalized_item["canceled_at"] = (
                    normalized_item.get("user_confirmed_at")
                    or normalized_item.get("created_at")
                )
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("tx_hash") is None
                and audit_item.get("tx_hash")
            ):
                normalized_item["tx_hash"] = audit_item["tx_hash"]
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("estimated_fee_eth") is None
                and audit_item.get("estimated_fee_eth") is not None
            ):
                normalized_item["estimated_fee_eth"] = audit_item["estimated_fee_eth"]
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("balance_before_eth") is None
                and audit_item.get("balance_before_eth") is not None
            ):
                normalized_item["balance_before_eth"] = audit_item["balance_before_eth"]
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("estimated_fee_eth") is None
                and legacy_total_cost is not None
            ):
                fee = (
                    Decimal(str(legacy_total_cost))
                    - Decimal(str(normalized_item["amount_eth"]))
                )
                normalized_item["estimated_fee_eth"] = format_eth_storage(fee)
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("estimated_fee_eth") is None
                and normalized_item.get("balance_before_eth") is not None
                and legacy_balance_after is not None
            ):
                fee = (
                    Decimal(str(normalized_item["balance_before_eth"]))
                    - Decimal(str(legacy_balance_after))
                    - Decimal(str(normalized_item["amount_eth"]))
                )
                normalized_item["estimated_fee_eth"] = format_eth_storage(fee)
                changed = True
            if (
                normalized_item.get("status") == "executed"
                and normalized_item.get("balance_before_eth") is None
                and legacy_balance_after is not None
                and normalized_item.get("estimated_fee_eth") is not None
            ):
                balance_before = (
                    Decimal(str(legacy_balance_after))
                    + Decimal(str(normalized_item["amount_eth"]))
                    + Decimal(str(normalized_item["estimated_fee_eth"]))
                )
                normalized_item["balance_before_eth"] = format_eth_storage(balance_before)
                changed = True
            if self._normalize_numeric_fields(normalized_item):
                changed = True
            for field in removed_fields:
                if field in normalized_item:
                    normalized_item.pop(field, None)
                    changed = True
            normalized.append(normalized_item)
        proposals = [Proposal.model_validate(item) for item in normalized]
        if changed:
            self.save_all(proposals)
        return proposals

    def save_all(self, proposals: list[Proposal]) -> None:
        items = []
        for item in proposals:
            dumped = item.model_dump(mode="json", exclude_none=True)
            self._normalize_numeric_fields(dumped)
            items.append(dumped)
        write_json(
            self.path,
            items,
        )

    def create(
        self,
        to: str,
        amount_eth: str,
        chain_id: int,
        *,
        requested_to: str | None = None,
        recipient_name: str | None = None,
    ) -> Proposal:
        normalized_amount_eth = format_eth_storage(amount_eth)
        amount_wei = str(Web3.to_wei(Decimal(normalized_amount_eth), "ether"))
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.demo_proposal_ttl_minutes
        )
        intent_raw = f"{to}|{amount_wei}|{chain_id}|ETH|{expires_at.isoformat()}"
        proposal = Proposal(
            proposal_id=f"proposal_{uuid4().hex[:8]}",
            requested_to=requested_to,
            recipient_name=recipient_name,
            to=to,
            amount_eth=normalized_amount_eth,
            amount_wei=amount_wei,
            chain_id=chain_id,
            intent_hash=hashlib.sha256(intent_raw.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
        proposals = self.list()
        proposals.append(proposal)
        self.save_all(proposals)
        return proposal

    def get(self, proposal_id: str) -> Proposal | None:
        for proposal in self.list():
            if proposal.proposal_id == proposal_id:
                return proposal
        return None

    def get_by_tx_hash(self, tx_hash: str) -> Proposal | None:
        for proposal in self.list():
            if proposal.tx_hash == tx_hash:
                return proposal
        return None

    def list_executed(self) -> list[Proposal]:
        proposals = [
            proposal
            for proposal in self.list()
            if proposal.status == "executed" and proposal.tx_hash
        ]
        proposals.sort(
            key=lambda proposal: proposal.executed_at or proposal.created_at,
            reverse=True,
        )
        return proposals

    def list_history(self) -> list[Proposal]:
        proposals = [
            proposal
            for proposal in self.list()
            if proposal.status == "executed"
            or proposal.status == "rejected"
        ]
        proposals.sort(
            key=lambda proposal: (
                proposal.executed_at
                or proposal.canceled_at
                or proposal.user_confirmed_at
                or proposal.created_at
            ),
            reverse=True,
        )
        return proposals

    def update_status(self, proposal_id: str, status: str, *, tx_hash: str | None = None) -> Proposal:
        return self.update(
            proposal_id,
            status=status,
            tx_hash=tx_hash,
        )

    def mark_local_authorized(
        self,
        proposal_id: str,
        *,
        user_confirmed_at: datetime | None,
        local_authorized_at: datetime,
        authorization_expires_at: datetime,
        authorization_token: str,
    ) -> Proposal:
        return self.update(
            proposal_id,
            status="authorized",
            user_confirmed_at=user_confirmed_at,
            local_authorized_at=local_authorized_at,
            authorization_expires_at=authorization_expires_at,
            authorization_token=authorization_token,
        )

    def mark_user_confirmed(
        self,
        proposal_id: str,
        *,
        status: str,
        user_confirmed_at: datetime,
    ) -> Proposal:
        return self.update(
            proposal_id,
            status=status,
            user_confirmed_at=user_confirmed_at,
        )

    def mark_executed(
        self,
        proposal_id: str,
        *,
        tx_hash: str,
        executed_at: datetime,
        estimated_fee_eth: str | None = None,
        balance_before_eth: str | None = None,
    ) -> Proposal:
        return self.update(
            proposal_id,
            status="executed",
            tx_hash=tx_hash,
            executed_at=executed_at,
            estimated_fee_eth=estimated_fee_eth,
            balance_before_eth=balance_before_eth,
        )

    def cancel(self, proposal_id: str, *, canceled_at: datetime) -> Proposal:
        return self.update(
            proposal_id,
            status="rejected",
            canceled_at=canceled_at,
            clear_local_authorization=True,
        )

    def consume_local_authorization(self, proposal_id: str) -> Proposal:
        return self.update(
            proposal_id,
            status="awaiting_local_authorization",
            clear_local_authorization=True,
        )

    def update(
        self,
        proposal_id: str,
        *,
        status: str | None = None,
        tx_hash: str | None = None,
        user_confirmed_at: datetime | None = None,
        local_authorized_at: datetime | None = None,
        authorization_expires_at: datetime | None = None,
        authorization_token: str | None = None,
        executed_at: datetime | None = None,
        canceled_at: datetime | None = None,
        estimated_fee_eth: str | None = None,
        balance_before_eth: str | None = None,
        clear_local_authorization: bool = False,
    ) -> Proposal:
        proposals = self.list()
        updated: Proposal | None = None
        for idx, proposal in enumerate(proposals):
            if proposal.proposal_id == proposal_id:
                update_data = {
                    "status": status or proposal.status,
                    "tx_hash": tx_hash or proposal.tx_hash,
                    "user_confirmed_at": user_confirmed_at
                    if user_confirmed_at is not None
                    else proposal.user_confirmed_at,
                    "local_authorized_at": local_authorized_at
                    if local_authorized_at is not None
                    else proposal.local_authorized_at,
                    "authorization_expires_at": None
                    if clear_local_authorization
                    else (
                        authorization_expires_at
                        if authorization_expires_at is not None
                        else proposal.authorization_expires_at
                    ),
                    "authorization_token": None
                    if clear_local_authorization
                    else (
                        authorization_token
                        if authorization_token is not None
                        else proposal.authorization_token
                    ),
                    "executed_at": executed_at
                    if executed_at is not None
                    else proposal.executed_at,
                    "canceled_at": canceled_at
                    if canceled_at is not None
                    else proposal.canceled_at,
                    "estimated_fee_eth": format_optional_eth_storage(
                        estimated_fee_eth
                        if estimated_fee_eth is not None
                        else proposal.estimated_fee_eth
                    ),
                    "balance_before_eth": format_optional_eth_storage(
                        balance_before_eth
                        if balance_before_eth is not None
                        else proposal.balance_before_eth
                    ),
                }
                updated = proposal.model_copy(update=update_data)
                proposals[idx] = updated
                break
        if updated is None:
            raise KeyError(f"提案不存在: {proposal_id}")
        self.save_all(proposals)
        return updated

    def _normalize_numeric_fields(self, item: dict) -> bool:
        changed = False
        for field in ("amount_eth", "estimated_fee_eth", "balance_before_eth"):
            value = item.get(field)
            if value is None:
                continue
            normalized = format_eth_storage(value)
            if normalized != value:
                item[field] = normalized
                changed = True
        return changed
