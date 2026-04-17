from __future__ import annotations

from datetime import UTC, datetime

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_view import build_proposal_detail, refresh_proposal


def handle(context: ToolContext, proposal_id: str) -> dict:
    proposal = refresh_proposal(context, proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")

    if proposal.status == "executed":
        raise PolicyError("提案已经执行完成，不能取消")

    if proposal.status == "rejected":
        result = build_proposal_detail(context, proposal)
        result["message"] = "提案之前已经取消，无需重复取消。"
        context.audit_store.append(
            "wallet_cancel_proposal",
            {"proposal_id": proposal_id, "status": proposal.status, "idempotent": True},
        )
        return result

    if proposal.status == "expired":
        result = build_proposal_detail(context, proposal)
        result["message"] = "提案已经过期，无需再取消。"
        context.audit_store.append(
            "wallet_cancel_proposal",
            {"proposal_id": proposal_id, "status": proposal.status, "idempotent": True},
        )
        return result

    proposal = context.proposal_store.cancel(
        proposal_id,
        canceled_at=datetime.now(UTC),
    )
    result = build_proposal_detail(context, proposal)
    result["message"] = "提案已取消，后续不能再确认或执行。"
    context.audit_store.append(
        "wallet_cancel_proposal",
        {"proposal_id": proposal_id, "status": proposal.status},
    )
    return result
