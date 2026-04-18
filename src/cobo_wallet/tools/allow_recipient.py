from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(
    context: ToolContext,
    *,
    target: str,
    name: str | None = None,
    note: str | None = None,
) -> dict:
    resolved = context.address_book_store.resolve(target)

    entry, created = context.whitelist_store.allow_entry(
        address=resolved["resolved_to"],
        name=name,
        note=note,
    )
    entries = context.whitelist_store.list()
    display_name = entry.name or entry.address
    result = {
        "message": (
            "已将该收款对象加入白名单。"
            if created
            else "该收款对象已经存在于白名单中，现已更新名称或备注。"
        ),
        "entry": entry.model_dump(mode="json", exclude_none=True),
        "count": len(entries),
        "whitelist_required": context.settings.demo_require_whitelist,
        "usage_hint": f"在白名单模式下，现在可以向 {display_name} 发起或执行转账。",
    }
    context.audit_store.append(
        "wallet_allow_recipient",
        {
            "target": target,
            "address": entry.address,
            "name": entry.name,
            "created": created,
        },
    )
    return result
