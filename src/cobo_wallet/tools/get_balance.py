from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    balance = context.wallet_service.get_balance()
    context.audit_store.append("wallet_get_balance", {"address": balance["address"]})
    return balance
