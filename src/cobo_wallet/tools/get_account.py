from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    account = context.wallet_service.get_account_summary()
    context.audit_store.append("wallet_get_account", account)
    return account
