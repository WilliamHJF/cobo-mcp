from __future__ import annotations

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools import confirm_transfer, request_local_authorization
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, proposal_id: str) -> dict:
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")

    if proposal.status == "executed":
        result = {
            "proposal_id": proposal.proposal_id,
            "status": proposal.status,
            "tx_hash": proposal.tx_hash,
            "ready_for_execution": False,
            "next_required_action": None,
            "message": "这条提案已经执行完成，无需再次执行。",
        }
        context.audit_store.append("wallet_execute_transfer", result)
        return result

    context.policy_engine.validate_recipient_whitelisted(
        address=proposal.to,
        whitelist_store=context.whitelist_store,
        requested_to=proposal.requested_to,
        recipient_name=proposal.recipient_name,
    )

    if context.settings.demo_require_local_authorization:
        if proposal.status in {"pending", "confirmed_by_user", "awaiting_local_authorization"}:
            result = request_local_authorization.handle(context, proposal_id=proposal_id)
            result.update(
                {
                    "ready_for_execution": False,
                    "next_required_action": "local_authorization",
                }
            )
            context.audit_store.append(
                "wallet_execute_transfer",
                {"proposal_id": proposal_id, "status": result["status"]},
            )
            return result

    result = confirm_transfer.handle(context, proposal_id=proposal_id)
    result.update(
        {
            "ready_for_execution": False,
            "next_required_action": None,
        }
    )
    context.audit_store.append(
        "wallet_execute_transfer",
        {"proposal_id": proposal_id, "tx_hash": result.get("tx_hash")},
    )
    return result
