from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, *, name_or_alias: str) -> dict:
    recipient = context.address_book_store.delete_entry(name_or_alias)
    all_recipients = context.address_book_store.list()
    result = {
        "message": "已删除收款人。",
        "deleted_recipient": recipient.model_dump(mode="json"),
        "recipient_count": len(all_recipients),
    }
    context.audit_store.append(
        "wallet_delete_recipient",
        {
            "target": name_or_alias,
            "deleted_name": recipient.name,
            "address": recipient.address,
        },
    )
    return result
