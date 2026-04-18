from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation

from dotenv import set_key
from eth_account import Account

from cobo_wallet.amounts import format_eth_display, format_eth_storage
from cobo_wallet.config.env import ENV_PATH, get_settings, reload_env_file
from cobo_wallet.server import build_context
from cobo_wallet.store.funding import FundingEventStore
from cobo_wallet.tools import (
    add_recipient,
    allow_recipient,
    delete_recipient,
    get_overview,
    list_proposals,
    list_transactions,
    revoke_recipient,
    update_recipient,
)


class OperatorError(ValueError):
    pass


class OperatorConsoleService:
    def __init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.settings = reload_env_file()
        self.context = build_context()
        self.funding_store = FundingEventStore(self.settings)

    def get_operator_pin(self) -> str:
        return self.settings.demo_operator_pin or self.settings.demo_approval_pin

    def verify_operator_pin(self, pin: str) -> None:
        if not pin or pin != self.get_operator_pin():
            raise OperatorError("管理员 PIN 不正确")

    def get_dashboard(self) -> dict:
        return {
            "overview": get_overview.handle(self.context),
            "recent_proposals": list_proposals.handle(self.context, limit=5),
            "recent_transactions": list_transactions.handle(self.context, limit=5),
            "recent_funding_events": self.funding_store.list(limit=5),
        }

    def get_wallet_config(self) -> dict:
        account = self.context.wallet_service.get_account_summary()
        return {
            "sepolia_rpc_url": self.settings.sepolia_rpc_url,
            "private_key_configured": bool(self.settings.demo_private_key),
            "derived_address": account["address"],
            "network": account["network"],
            "chain_id": account["chain_id"],
        }

    def update_wallet_config(
        self,
        *,
        sepolia_rpc_url: str,
        private_key: str | None,
        clear_private_key: bool = False,
    ) -> dict:
        derived_address = None
        updates = {
            "SEPOLIA_RPC_URL": sepolia_rpc_url.strip(),
        }

        if clear_private_key:
            updates["DEMO_PRIVATE_KEY"] = ""
        elif private_key is not None and private_key.strip():
            candidate = private_key.strip()
            try:
                derived_address = Account.from_key(candidate).address
            except Exception as exc:  # noqa: BLE001
                raise OperatorError("私钥格式不正确，无法派生地址") from exc
            updates["DEMO_PRIVATE_KEY"] = candidate
        else:
            derived_address = None

        self._write_env_updates(updates)
        self.context.audit_store.append(
            "operator_update_wallet_config",
            {
                "rpc_configured": bool(updates["SEPOLIA_RPC_URL"]),
                "private_key_updated": (
                    clear_private_key
                    or bool(private_key and private_key.strip())
                ),
                "derived_address": derived_address,
            },
        )
        self.refresh()
        return self.get_wallet_config()

    def get_policy_config(self) -> dict:
        return {
            "write_enabled": self.settings.demo_write_enabled,
            "execution_mode": self.settings.demo_execution_mode,
            "require_whitelist": self.settings.demo_require_whitelist,
            "require_local_auth": self.settings.demo_require_local_authorization,
            "max_transfer_eth": format_eth_display(self.settings.demo_max_transfer_eth),
            "proposal_ttl_minutes": self.settings.demo_proposal_ttl_minutes,
            "local_auth_ttl_minutes": self.settings.demo_local_authorization_ttl_minutes,
            "operator_pin_configured": bool(self.get_operator_pin()),
        }

    def update_policy_config(
        self,
        *,
        write_enabled: bool,
        execution_mode: str,
        require_whitelist: bool,
        require_local_auth: bool,
        max_transfer_eth: str,
        proposal_ttl_minutes: int,
        local_auth_ttl_minutes: int,
        operator_pin: str | None,
    ) -> dict:
        max_amount = self._normalize_decimal_string(max_transfer_eth, "单笔限额")
        if proposal_ttl_minutes <= 0:
            raise OperatorError("提案有效期必须大于 0")
        if local_auth_ttl_minutes <= 0:
            raise OperatorError("本地授权有效期必须大于 0")
        if execution_mode not in {"simulate", "sepolia"}:
            raise OperatorError("执行模式只支持 simulate 或 sepolia")

        updates = {
            "DEMO_WRITE_ENABLED": self._format_bool(write_enabled),
            "DEMO_EXECUTION_MODE": execution_mode,
            "DEMO_REQUIRE_WHITELIST": self._format_bool(require_whitelist),
            "DEMO_REQUIRE_LOCAL_AUTH": self._format_bool(require_local_auth),
            "DEMO_MAX_TRANSFER_ETH": max_amount,
            "DEMO_PROPOSAL_TTL_MINUTES": str(proposal_ttl_minutes),
            "DEMO_LOCAL_AUTH_TTL_MINUTES": str(local_auth_ttl_minutes),
        }
        if operator_pin is not None and operator_pin.strip():
            updates["DEMO_OPERATOR_PIN"] = operator_pin.strip()

        self._write_env_updates(updates)
        self.context.audit_store.append(
            "operator_update_policy",
            {
                "write_enabled": write_enabled,
                "execution_mode": execution_mode,
                "require_whitelist": require_whitelist,
                "require_local_auth": require_local_auth,
                "max_transfer_eth": max_amount,
            },
        )
        self.refresh()
        return self.get_policy_config()

    def list_funding_events(self, limit: int = 20) -> list[dict]:
        return self.funding_store.list(limit=limit)

    def deposit_balance(
        self,
        *,
        amount_eth: str,
        source_label: str,
        note: str | None,
    ) -> dict:
        amount = self._normalize_decimal(amount_eth, "入金额度")
        if amount <= 0:
            raise OperatorError("入金额度必须大于 0")
        state_store = self.context.wallet_service.wallet_state_store
        balance_before = state_store.get_balance_eth()
        balance_after = balance_before + amount
        state_store.set_balance_eth(balance_after)
        event = self.funding_store.append(
            {
                "event_type": "deposit",
                "amount_eth": self._format_decimal(amount),
                "balance_before_eth": self._format_decimal(balance_before),
                "balance_after_eth": self._format_decimal(balance_after),
                "source_label": source_label.strip() or None,
                "note": note.strip() if note else None,
            }
        )
        self.context.audit_store.append("operator_deposit_balance", event)
        self.refresh()
        return event

    def withdraw_balance(
        self,
        *,
        amount_eth: str,
        target_label: str,
        note: str | None,
    ) -> dict:
        amount = self._normalize_decimal(amount_eth, "出金额度")
        if amount <= 0:
            raise OperatorError("出金额度必须大于 0")
        state_store = self.context.wallet_service.wallet_state_store
        balance_before = state_store.get_balance_eth()
        if amount > balance_before:
            raise OperatorError("模拟余额不足，不能执行人工出金")
        balance_after = balance_before - amount
        state_store.set_balance_eth(balance_after)
        event = self.funding_store.append(
            {
                "event_type": "withdraw",
                "amount_eth": self._format_decimal(amount),
                "balance_before_eth": self._format_decimal(balance_before),
                "balance_after_eth": self._format_decimal(balance_after),
                "target_label": target_label.strip() or None,
                "note": note.strip() if note else None,
            }
        )
        self.context.audit_store.append("operator_withdraw_balance", event)
        self.refresh()
        return event

    def set_balance(
        self,
        *,
        target_balance_eth: str,
        note: str | None,
    ) -> dict:
        target_balance = self._normalize_decimal(target_balance_eth, "目标余额")
        if target_balance < 0:
            raise OperatorError("目标余额不能小于 0")
        state_store = self.context.wallet_service.wallet_state_store
        balance_before = state_store.get_balance_eth()
        state_store.set_balance_eth(target_balance)
        event = self.funding_store.append(
            {
                "event_type": "set_balance",
                "amount_eth": None,
                "balance_before_eth": self._format_decimal(balance_before),
                "balance_after_eth": self._format_decimal(target_balance),
                "note": note.strip() if note else None,
            }
        )
        self.context.audit_store.append("operator_set_balance", event)
        self.refresh()
        return event

    def add_whitelist_entry(
        self,
        *,
        target: str,
        name: str | None,
        note: str | None,
    ) -> dict:
        result = allow_recipient.handle(
            self.context,
            target=target,
            name=name.strip() if name else None,
            note=note.strip() if note else None,
        )
        self.context.audit_store.append(
            "operator_allow_recipient",
            {"target": target, "entry": result["entry"]},
        )
        return result

    def revoke_whitelist_entry(self, target: str) -> dict:
        result = revoke_recipient.handle(self.context, target=target)
        self.context.audit_store.append(
            "operator_revoke_recipient",
            {"target": target},
        )
        return result

    def add_address_book_entry(
        self,
        *,
        name: str,
        address: str,
        aliases: list[str],
        note: str | None,
    ) -> dict:
        result = add_recipient.handle(
            self.context,
            name=name,
            address=address,
            aliases=aliases,
            note=note.strip() if note else None,
        )
        self.context.audit_store.append(
            "operator_add_recipient",
            {"name": name, "address": address},
        )
        return result

    def update_address_book_entry(
        self,
        *,
        name_or_alias: str,
        name: str | None,
        address: str | None,
        aliases: list[str] | None,
        note: str | None,
    ) -> dict:
        result = update_recipient.handle(
            self.context,
            name_or_alias=name_or_alias,
            name=name.strip() if name else None,
            address=address.strip() if address else None,
            aliases=aliases,
            note=note.strip() if note else None,
        )
        self.context.audit_store.append(
            "operator_update_recipient",
            {"target": name_or_alias},
        )
        return result

    def delete_address_book_entry(self, name_or_alias: str) -> dict:
        result = delete_recipient.handle(self.context, name_or_alias=name_or_alias)
        self.context.audit_store.append(
            "operator_delete_recipient",
            {"target": name_or_alias},
        )
        return result

    def _write_env_updates(self, updates: dict[str, str]) -> None:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        ENV_PATH.touch(exist_ok=True)
        for key, value in updates.items():
            set_key(
                str(ENV_PATH),
                key,
                value,
                quote_mode="never",
            )
            os.environ[key] = value
        reload_env_file()

    def _normalize_decimal(self, value: str, field_name: str) -> Decimal:
        try:
            return Decimal(value.strip())
        except (InvalidOperation, AttributeError) as exc:
            raise OperatorError(f"{field_name}格式不正确") from exc

    def _normalize_decimal_string(self, value: str, field_name: str) -> str:
        amount = self._normalize_decimal(value, field_name)
        if amount <= 0:
            raise OperatorError(f"{field_name}必须大于 0")
        return self._format_decimal(amount)

    def _format_decimal(self, value: Decimal) -> str:
        return format_eth_storage(value)

    def _format_bool(self, value: bool) -> str:
        return "true" if value else "false"
