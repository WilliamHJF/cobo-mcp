from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(
    context: ToolContext,
    *,
    name: str,
    address: str,
    aliases: list[str] | None = None,
    note: str | None = None,
) -> dict:
    recipient = context.address_book_store.add_entry(
        name=name,
        address=address,
        aliases=aliases,
        note=note,
    )
    all_recipients = context.address_book_store.list()
    result = {
        "message": "已新增收款人。之后可以直接把 to 写成这个名称或别名。",
        "recipient": recipient.model_dump(mode="json"),
        "recipient_count": len(all_recipients),
        "usage_hint": f"现在可以直接说：帮我向 {recipient.name} 转 0.01 ETH",
    }
    context.audit_store.append(
        "wallet_add_recipient",
        {
            "name": recipient.name,
            "address": recipient.address,
            "aliases": recipient.aliases,
        },
    )
    return result
