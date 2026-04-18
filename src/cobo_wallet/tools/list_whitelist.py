from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def _serialize_entry(context: ToolContext, entry) -> dict:
    item = entry.model_dump(mode="json", exclude_none=True)
    recipient = context.address_book_store.get_by_address(entry.address)
    if recipient is not None:
        item["recipient_name"] = recipient.name
        if recipient.note:
            item["recipient_note"] = recipient.note
    if "name" not in item and recipient is not None:
        item["name"] = recipient.name
    if "note" not in item and recipient is not None and recipient.note:
        item["note"] = recipient.note
    return item


def handle(context: ToolContext) -> dict:
    entries = [
        _serialize_entry(context, entry)
        for entry in context.whitelist_store.list()
    ]
    result = {
        "count": len(entries),
        "whitelist_required": context.settings.demo_require_whitelist,
        "entries": entries,
        "message": (
            "返回当前白名单。只有白名单中的地址，才允许在白名单模式下发起或执行转账。"
            if entries
            else "当前白名单为空。开启白名单模式后，空白名单会阻止所有转账。"
        ),
    }
    context.audit_store.append(
        "wallet_list_whitelist",
        {"count": len(entries), "whitelist_required": context.settings.demo_require_whitelist},
    )
    return result
