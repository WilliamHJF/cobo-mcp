from __future__ import annotations

from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.preview import (
    build_confirmation_preview,
    build_recipient_preview,
)


def handle(context: ToolContext, to: str, amount: str) -> dict:
    context.policy_engine.validate_chain_id(context.settings.demo_chain_id)
    normalized_amount = context.policy_engine.normalize_amount(amount)
    recipient = context.address_book_store.resolve(to)
    result = context.wallet_service.estimate_transfer(
        to=recipient["resolved_to"],
        amount_eth=normalized_amount,
    )
    result.update(
        {
            "requested_to": recipient["requested_to"],
            "resolved_to": recipient["resolved_to"],
            "recipient_name": recipient["recipient_name"],
            "matched_by": recipient["matched_by"],
        }
    )
    recipient_preview = build_recipient_preview(
        requested_to=recipient["requested_to"],
        resolved_to=recipient["resolved_to"],
        recipient_name=recipient["recipient_name"],
        matched_by=recipient["matched_by"],
    )
    result["recipient_preview"] = recipient_preview
    result["confirmation_preview"] = build_confirmation_preview(
        recipient_preview=recipient_preview,
        amount_eth=normalized_amount,
        estimated_fee_eth=result["estimated_fee_eth"],
        estimated_total_cost_eth=result["estimated_total_cost_eth"],
    )
    result["assistant_confirmation_hint"] = (
        "请优先直接展示 confirmation_preview.confirmation_markdown；只有在用户明确回复确认后，才能进入 wallet_confirm_proposal。"
    )
    context.audit_store.append(
        "wallet_estimate_transfer",
        {
            "requested_to": recipient["requested_to"],
            "resolved_to": recipient["resolved_to"],
            "recipient_name": recipient["recipient_name"],
            "amount": normalized_amount,
        },
    )
    return result
