from __future__ import annotations

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_view import build_proposal_detail, refresh_proposal


def handle(context: ToolContext, proposal_id: str) -> dict:
    proposal = refresh_proposal(context, proposal_id)
    if proposal is None:
        raise PolicyError("提案不存在")

    result = build_proposal_detail(context, proposal)
    context.audit_store.append(
        "wallet_get_proposal",
        {"proposal_id": proposal_id, "status": proposal.status},
    )
    return result
