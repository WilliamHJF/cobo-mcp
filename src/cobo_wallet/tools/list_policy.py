from __future__ import annotations

from cobo_wallet.config.policy import build_policy_snapshot
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    snapshot = build_policy_snapshot(context.settings).model_dump(mode="json")
    context.audit_store.append("wallet_list_policy", snapshot)
    return snapshot
