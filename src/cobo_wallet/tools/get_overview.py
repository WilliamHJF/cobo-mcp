from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    account = context.wallet_service.get_account_summary()
    balance = context.wallet_service.get_balance()
    policy = {
        "chain_id": context.settings.demo_chain_id,
        "write_enabled": context.settings.demo_write_enabled,
        "execution_mode": context.settings.demo_execution_mode,
        "max_transfer_eth": context.settings.demo_max_transfer_eth,
        "proposal_ttl_minutes": context.settings.demo_proposal_ttl_minutes,
        "local_authorization_required": context.settings.demo_require_local_authorization,
    }
    recipients = context.address_book_store.list()
    result = {
        "account": account,
        "balance": balance,
        "policy": policy,
        "recipient_count": len(recipients),
        "recommended_flow": [
            "wallet_list_recipients",
            "wallet_prepare_transfer",
            "wallet_confirm_proposal",
            "wallet_execute_transfer",
            "wallet_get_transaction_status",
        ],
        "recipient_management_tools": [
            "wallet_add_recipient",
            "wallet_update_recipient",
            "wallet_delete_recipient",
        ],
        "history_tools": ["wallet_list_transactions"],
        "proposal_tools": ["wallet_get_proposal", "wallet_cancel_proposal"],
    }
    context.audit_store.append("wallet_get_overview", {"recipient_count": len(recipients)})
    return result
