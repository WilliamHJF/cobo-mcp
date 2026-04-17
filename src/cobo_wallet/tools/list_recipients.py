from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    recipients = [
        item.model_dump(mode="json") for item in context.address_book_store.list()
    ]
    result = {
        "count": len(recipients),
        "recipients": recipients,
        "message": (
            "你可以把 to 参数写成完整地址，或者直接写这里的 name / aliases。"
            "如果要维护地址簿，可调用 wallet_add_recipient / wallet_update_recipient / wallet_delete_recipient。"
        ),
    }
    context.audit_store.append("wallet_list_recipients", {"count": len(recipients)})
    return result
