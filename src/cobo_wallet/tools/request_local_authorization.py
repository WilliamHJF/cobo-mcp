from __future__ import annotations

from datetime import UTC, datetime

from cobo_wallet.amounts import format_eth_display
from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, proposal_id: str) -> dict:
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")
    if not context.settings.demo_require_local_authorization:
        if proposal.status == "confirmed_by_user":
            message = "当前配置已关闭本地 PIN 授权，而且这条提案已经记录用户确认，现在可以直接调用 wallet_execute_transfer。"
            next_required_action = "execute_transfer"
        elif proposal.status == "executed":
            message = "当前配置已关闭本地 PIN 授权，而且这条提案已经执行完成，无需再请求授权。"
            next_required_action = None
        else:
            message = "当前配置已关闭本地 PIN 授权。请在用户明确回复确认后调用 wallet_confirm_proposal，而不是调用这个工具。"
            next_required_action = "confirm_proposal"
        result = {
            "proposal_id": proposal.proposal_id,
            "status": proposal.status,
            "requested_to": proposal.requested_to,
            "recipient_name": proposal.recipient_name,
            "to": proposal.to,
            "amount_eth": format_eth_display(proposal.amount_eth),
            "local_authorization_required": False,
            "local_authorization_ttl_minutes": None,
            "authorization_expires_at": None,
            "local_authorization_command": None,
            "next_required_action": next_required_action,
            "message": message,
        }
        context.audit_store.append(
            "wallet_request_local_authorization",
            {"proposal_id": proposal_id, "status": proposal.status},
        )
        return result
    now = datetime.now(UTC)
    if proposal.expires_at < now:
        context.proposal_store.update_status(proposal_id, "expired")
        raise PolicyError("提案已过期")
    if proposal.status == "executed":
        raise PolicyError("提案已经执行过，不能再次请求授权")
    if proposal.status == "rejected":
        raise PolicyError("提案已被拒绝，不能请求授权")
    context.policy_engine.validate_recipient_whitelisted(
        address=proposal.to,
        whitelist_store=context.whitelist_store,
        requested_to=proposal.requested_to,
        recipient_name=proposal.recipient_name,
    )

    if (
        proposal.status == "authorized"
        and (
            proposal.authorization_expires_at is None
            or proposal.authorization_expires_at < now
            or not proposal.authorization_token
        )
    ):
        proposal = context.proposal_store.consume_local_authorization(proposal_id)

    if proposal.status == "pending":
        proposal = context.proposal_store.mark_user_confirmed(
            proposal_id,
            status="awaiting_local_authorization",
            user_confirmed_at=now,
        )
    elif proposal.status == "confirmed_by_user":
        proposal = context.proposal_store.update_status(
            proposal_id, "awaiting_local_authorization"
        )

    if proposal.status not in {"awaiting_local_authorization", "authorized"}:
        raise PolicyError(f"当前提案状态不支持请求授权: {proposal.status}")

    command = f"uv run cobo-wallet-authorize --proposal-id {proposal_id}"
    if proposal.status == "authorized":
        message = "这笔提案已经完成本地 PIN 授权，可以直接调用 wallet_execute_transfer。"
    else:
        message = "请在本地终端执行授权命令并输入 PIN，授权完成后再调用 wallet_execute_transfer。"
    result = {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status,
        "requested_to": proposal.requested_to,
        "recipient_name": proposal.recipient_name,
        "to": proposal.to,
        "amount_eth": format_eth_display(proposal.amount_eth),
        "local_authorization_required": True,
        "local_authorization_ttl_minutes": context.settings.demo_local_authorization_ttl_minutes,
        "authorization_expires_at": proposal.authorization_expires_at,
        "local_authorization_command": command,
        "message": message,
    }
    context.audit_store.append(
        "wallet_request_local_authorization",
        {"proposal_id": proposal_id, "status": proposal.status},
    )
    return result
