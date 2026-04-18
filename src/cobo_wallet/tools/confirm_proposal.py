from __future__ import annotations

from datetime import UTC, datetime

from cobo_wallet.amounts import format_eth_display
from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, proposal_id: str) -> dict:
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")

    now = datetime.now(UTC)
    if proposal.expires_at < now:
        context.proposal_store.update_status(proposal_id, "expired")
        raise PolicyError("提案已过期")
    if proposal.status == "rejected":
        raise PolicyError("提案已被拒绝，不能确认")
    if proposal.status == "executed":
        return {
            "proposal_id": proposal.proposal_id,
            "status": proposal.status,
            "requested_to": proposal.requested_to,
            "recipient_name": proposal.recipient_name,
            "to": proposal.to,
            "amount_eth": format_eth_display(proposal.amount_eth),
            "user_confirmed": True,
            "ready_for_execution": False,
            "next_required_action": None,
            "message": "这条提案已经执行完成，无需再次确认。",
        }

    context.policy_engine.validate_recipient_whitelisted(
        address=proposal.to,
        whitelist_store=context.whitelist_store,
        requested_to=proposal.requested_to,
        recipient_name=proposal.recipient_name,
    )

    if context.settings.demo_require_local_authorization:
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

        if proposal.status == "awaiting_local_authorization":
            result = {
                "proposal_id": proposal.proposal_id,
                "status": proposal.status,
                "requested_to": proposal.requested_to,
                "recipient_name": proposal.recipient_name,
                "to": proposal.to,
                "amount_eth": format_eth_display(proposal.amount_eth),
                "user_confirmed": True,
                "ready_for_execution": False,
                "next_required_action": "local_authorization",
                "local_authorization_required": True,
                "local_authorization_command": (
                    f"uv run cobo-wallet-authorize --proposal-id {proposal_id}"
                ),
                "message": "已记录用户确认。下一步需要完成本地 PIN 授权，之后才能执行转账。",
            }
            context.audit_store.append(
                "wallet_confirm_proposal",
                {"proposal_id": proposal_id, "status": proposal.status},
            )
            return result

        if proposal.status == "authorized":
            result = {
                "proposal_id": proposal.proposal_id,
                "status": proposal.status,
                "requested_to": proposal.requested_to,
                "recipient_name": proposal.recipient_name,
                "to": proposal.to,
                "amount_eth": format_eth_display(proposal.amount_eth),
                "user_confirmed": True,
                "ready_for_execution": True,
                "next_required_action": "execute_transfer",
                "local_authorization_required": True,
                "message": "这条提案已经完成用户确认和本地授权，现在可以调用 wallet_execute_transfer。",
            }
            context.audit_store.append(
                "wallet_confirm_proposal",
                {"proposal_id": proposal_id, "status": proposal.status},
            )
            return result

        raise PolicyError(f"当前提案状态不支持确认: {proposal.status}")

    if proposal.status == "pending":
        proposal = context.proposal_store.mark_user_confirmed(
            proposal_id,
            status="confirmed_by_user",
            user_confirmed_at=now,
        )

    if proposal.status != "confirmed_by_user":
        raise PolicyError(f"当前提案状态不支持确认: {proposal.status}")

    result = {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status,
        "requested_to": proposal.requested_to,
        "recipient_name": proposal.recipient_name,
        "to": proposal.to,
        "amount_eth": format_eth_display(proposal.amount_eth),
        "user_confirmed": True,
        "ready_for_execution": True,
        "next_required_action": "execute_transfer",
        "local_authorization_required": False,
        "message": "已记录用户确认。现在才可以调用 wallet_execute_transfer 执行这笔转账。",
    }
    context.audit_store.append(
        "wallet_confirm_proposal",
        {"proposal_id": proposal_id, "status": proposal.status},
    )
    return result
