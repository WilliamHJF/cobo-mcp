from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    account = context.wallet_service.get_account_summary()
    balance = context.wallet_service.get_balance()
    balance_source_info = context.wallet_service.get_balance_source_info()
    recommended_flow = ["wallet_list_recipients"]
    if context.settings.demo_require_whitelist:
        recommended_flow.append("wallet_list_whitelist")
    recommended_flow.extend(
        [
            "wallet_prepare_transfer",
            "wallet_confirm_proposal",
            "wallet_execute_transfer",
            "wallet_get_transaction_status",
        ]
    )
    policy = {
        "chain_id": context.settings.demo_chain_id,
        "write_enabled": context.settings.demo_write_enabled,
        "execution_mode": context.settings.demo_execution_mode,
        "max_transfer_eth": context.settings.demo_max_transfer_eth,
        "proposal_ttl_minutes": context.settings.demo_proposal_ttl_minutes,
        "local_authorization_required": context.settings.demo_require_local_authorization,
        "whitelist_required": context.settings.demo_require_whitelist,
    }
    recipients = context.address_book_store.list()
    whitelist_entries = context.whitelist_store.list()
    result = {
        "account": account,
        "balance": balance,
        "state_management": balance_source_info,
        "policy": policy,
        "recipient_count": len(recipients),
        "whitelist_count": len(whitelist_entries),
        "recommended_flow": recommended_flow,
        "recipient_management_tools": [
            "wallet_add_recipient",
            "wallet_update_recipient",
            "wallet_delete_recipient",
        ],
        "receive_tools": ["wallet_get_receive_card"],
        "whitelist_tools": [
            "wallet_list_whitelist",
            "wallet_allow_recipient",
            "wallet_revoke_recipient",
        ],
        "history_tools": ["wallet_list_transactions"],
        "proposal_tools": [
            "wallet_list_proposals",
            "wallet_get_proposal",
            "wallet_cancel_proposal",
        ],
    }
    context.audit_store.append(
        "wallet_get_overview",
        {
            "recipient_count": len(recipients),
            "whitelist_count": len(whitelist_entries),
            "balance_source": balance_source_info["balance_source"],
        },
    )
    return result
