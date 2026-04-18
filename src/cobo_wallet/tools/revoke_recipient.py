from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext, *, target: str) -> dict:
    entry = context.whitelist_store.revoke_entry(target)
    entries = context.whitelist_store.list()
    result = {
        "message": "已从白名单移除该收款对象。后续在白名单模式下将不能再向这个地址转账。",
        "revoked_entry": entry.model_dump(mode="json", exclude_none=True),
        "count": len(entries),
        "whitelist_required": context.settings.demo_require_whitelist,
    }
    context.audit_store.append(
        "wallet_revoke_recipient",
        {
            "target": target,
            "address": entry.address,
            "name": entry.name,
        },
    )
    return result
