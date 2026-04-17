from __future__ import annotations

from datetime import UTC, datetime

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, proposal_id: str) -> dict:
    context.policy_engine.validate_write_enabled()
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")
    now = datetime.now(UTC)
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
        context.proposal_store.consume_local_authorization(proposal_id)
    elif proposal.status != "confirmed_by_user":
        if proposal.status == "pending":
            raise PolicyError("提案还没有记录用户确认，请先调用 wallet_confirm_proposal")
        raise PolicyError(f"当前提案状态不允许执行: {proposal.status}")

    context.policy_engine.validate_proposal_executable(proposal)
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
