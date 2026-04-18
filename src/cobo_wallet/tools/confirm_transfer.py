from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime

from web3 import Web3

from cobo_wallet.amounts import format_eth_storage
from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext


def _build_amount_integrity_payload(proposal_id: str, proposal, expected_amount_wei: str) -> dict:
    return {
        "proposal_id": proposal_id,
        "stored_intent_hash": proposal.intent_hash,
        "to": proposal.to,
        "amount_eth": proposal.amount_eth,
        "amount_wei": proposal.amount_wei,
        "expected_amount_wei": expected_amount_wei,
        "chain_id": proposal.chain_id,
    }


def handle(context: ToolContext, proposal_id: str) -> dict:
    context.policy_engine.validate_write_enabled()
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")
    now = datetime.now(UTC)
    should_consume_local_authorization = False
    if proposal.expires_at < now:
        context.proposal_store.update_status(proposal_id, "expired")
        raise PolicyError("提案已过期")
    if proposal.status == "executed":
        raise PolicyError("提案已经执行过，不能重复执行")
    if proposal.status == "rejected":
        raise PolicyError("提案已被拒绝，不能执行")
    if context.settings.demo_require_local_authorization:
        if proposal.status == "pending":
            raise PolicyError("提案还没有记录用户确认，请先调用 wallet_confirm_proposal")
        if proposal.status == "confirmed_by_user":
            raise PolicyError("提案已经记录用户确认，但还没有完成本地授权")
        if proposal.status == "awaiting_local_authorization":
            raise PolicyError("提案尚未完成本地 PIN 授权")
        if proposal.status != "authorized":
            raise PolicyError(f"当前提案状态不允许执行: {proposal.status}")
        if not proposal.authorization_token or proposal.authorization_expires_at is None:
            context.proposal_store.consume_local_authorization(proposal_id)
            raise PolicyError("本地授权不存在或已失效，请重新执行本地授权")
        if proposal.authorization_expires_at < now:
            context.proposal_store.consume_local_authorization(proposal_id)
            raise PolicyError("本地授权已过期，请重新执行本地授权")
        should_consume_local_authorization = True
    elif proposal.status != "confirmed_by_user":
        if proposal.status == "pending":
            raise PolicyError("提案还没有记录用户确认，请先调用 wallet_confirm_proposal")
        raise PolicyError(f"当前提案状态不允许执行: {proposal.status}")

    expected_intent_hash = context.proposal_store.get_expected_intent_hash(proposal)
    if proposal.intent_hash != expected_intent_hash:
        context.audit_store.append(
            "wallet_intent_integrity_failed",
            {
                "proposal_id": proposal_id,
                "stored_intent_hash": proposal.intent_hash,
                "expected_intent_hash": expected_intent_hash,
                "to": proposal.to,
                "amount_eth": proposal.amount_eth,
                "chain_id": proposal.chain_id,
            },
        )
        raise PolicyError(
            "提案核心交易意图校验失败，当前执行参数与提案创建时记录的意图不一致，已拒绝执行。"
        )

    expected_amount_wei = str(
        Web3.to_wei(Decimal(format_eth_storage(proposal.amount_eth)), "ether")
    )
    if proposal.amount_wei != expected_amount_wei:
        context.audit_store.append(
            "wallet_intent_integrity_failed",
            _build_amount_integrity_payload(
                proposal_id,
                proposal,
                expected_amount_wei,
            ),
        )
        raise PolicyError(
            "提案金额完整性校验失败，amount_eth 与 amount_wei 不一致，已拒绝执行。"
        )

    context.policy_engine.validate_recipient_whitelisted(
        address=proposal.to,
        whitelist_store=context.whitelist_store,
        requested_to=proposal.requested_to,
        recipient_name=proposal.recipient_name,
    )
    context.policy_engine.validate_proposal_executable(proposal)
    if should_consume_local_authorization:
        context.proposal_store.consume_local_authorization(proposal_id)
    result = context.wallet_service.confirm_and_send(proposal)
    context.proposal_store.mark_executed(
        proposal_id,
        tx_hash=result.get("tx_hash"),
        executed_at=datetime.now(UTC),
        estimated_fee_eth=result.get("estimated_fee_eth"),
        balance_before_eth=result.get("balance_before_eth"),
    )
    context.audit_store.append(
        "wallet_confirm_transfer",
        {"proposal_id": proposal_id, "result": result},
    )
    return result
