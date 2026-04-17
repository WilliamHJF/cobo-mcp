from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(
    context: ToolContext,
    *,
    name_or_alias: str,
    name: str | None = None,
    address: str | None = None,
    aliases: list[str] | None = None,
    note: str | None = None,
) -> dict:
    before, after = context.address_book_store.update_entry(
        name_or_alias,
        name=name,
        address=address,
        aliases=aliases,
        note=note,
    )
    result = {
        "message": "已更新收款人配置。",
        "before": before.model_dump(mode="json"),
        "recipient": after.model_dump(mode="json"),
        "usage_hint": f"之后可以直接把 to 写成 {after.name} 或它的 aliases。",
    }
    context.audit_store.append(
        "wallet_update_recipient",
        {
            "target": name_or_alias,
            "before_name": before.name,
            "after_name": after.name,
            "address": after.address,
            "aliases": after.aliases,
        },
    )
    return result
