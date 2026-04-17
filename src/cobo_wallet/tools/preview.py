from __future__ import annotations


def _short_address(address: str) -> str:
    if len(address) < 12:
        return address
    return f"{address[:6]}...{address[-4:]}"


def build_recipient_preview(
    *,
    requested_to: str,
    resolved_to: str,
    recipient_name: str | None,
    matched_by: str,
) -> dict:
    uses_alias = matched_by in {"name", "alias"}
    if recipient_name:
        display_text = f"{recipient_name} <{resolved_to}>"
    else:
        display_text = resolved_to

    return {
        "requested_to": requested_to,
        "recipient_name": recipient_name,
        "resolved_to": resolved_to,
        "matched_by": matched_by,
        "uses_address_alias": uses_alias,
        "short_address": _short_address(resolved_to),
        "display_text": display_text,
    }


def build_confirmation_preview(
    *,
    recipient_preview: dict,
    amount_eth: str,
    estimated_fee_eth: str,
    estimated_total_cost_eth: str,
) -> dict:
    review_items = [
        f"收款人: {recipient_preview['display_text']}",
        f"实际地址: {recipient_preview['resolved_to']}",
        f"转账金额: {amount_eth} ETH",
        f"预估手续费: {estimated_fee_eth} ETH",
        f"总成本: {estimated_total_cost_eth} ETH",
        "是否确认: 请回复“确认”或“取消”",
    ]
    confirmation_markdown = "\n".join(
        [
            "请确认以下转账信息：",
            "",
            f"- 收款人：`{recipient_preview['display_text']}`",
            f"- 实际地址：`{recipient_preview['resolved_to']}`",
            f"- 转账金额：`{amount_eth} ETH`",
            f"- 预估手续费：`{estimated_fee_eth} ETH`",
            f"- 总成本：`{estimated_total_cost_eth} ETH`",
            "",
            "请回复“确认”或“取消”。",
        ]
    )
    return {
        "recipient_name": recipient_preview["recipient_name"],
        "requested_to": recipient_preview["requested_to"],
        "resolved_to": recipient_preview["resolved_to"],
        "display_text": recipient_preview["display_text"],
        "short_address": recipient_preview["short_address"],
        "amount_eth": amount_eth,
        "estimated_fee_eth": estimated_fee_eth,
        "estimated_total_cost_eth": estimated_total_cost_eth,
        "review_items": review_items,
        "confirmation_card": {
            "title": "转账确认",
            "fields": [
                {"label": "收款人", "value": recipient_preview["display_text"]},
                {"label": "实际地址", "value": recipient_preview["resolved_to"]},
                {"label": "转账金额", "value": f"{amount_eth} ETH"},
                {"label": "预估手续费", "value": f"{estimated_fee_eth} ETH"},
                {"label": "总成本", "value": f"{estimated_total_cost_eth} ETH"},
                {"label": "是否确认", "value": "请回复“确认”或“取消”"},
            ],
        },
        "confirmation_markdown": confirmation_markdown,
    }
