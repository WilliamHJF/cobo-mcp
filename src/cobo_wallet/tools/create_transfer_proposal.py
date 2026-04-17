from __future__ import annotations

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_derived import dump_proposal
from cobo_wallet.tools.preview import (
    build_confirmation_preview,
    build_recipient_preview,
)


def handle(context: ToolContext, to: str, amount: str) -> dict:
    context.policy_engine.validate_chain_id(context.settings.demo_chain_id)
    normalized_amount = context.policy_engine.normalize_amount(amount)
    recipient = context.address_book_store.resolve(to)
    quote = context.wallet_service.estimate_transfer(
        to=recipient["resolved_to"],
        amount_eth=normalized_amount,
    )
    quote.update(
        {
            "requested_to": recipient["requested_to"],
            "resolved_to": recipient["resolved_to"],
            "recipient_name": recipient["recipient_name"],
            "matched_by": recipient["matched_by"],
        }
    )
    if not quote["balance_sufficient"]:
        raise PolicyError(
            "当前余额不足，不能创建提案。"
            f"当前余额 {quote['current_balance_eth']} ETH，"
            f"预计总成本 {quote['required_total_eth']} ETH。"
        )
    recipient_preview = build_recipient_preview(
        requested_to=recipient["requested_to"],
        resolved_to=recipient["resolved_to"],
        recipient_name=recipient["recipient_name"],
        matched_by=recipient["matched_by"],
    )
    confirmation_preview = build_confirmation_preview(
        recipient_preview=recipient_preview,
        amount_eth=normalized_amount,
        estimated_fee_eth=quote["estimated_fee_eth"],
        estimated_total_cost_eth=quote["estimated_total_cost_eth"],
    )
    proposal = context.proposal_store.create(
        to=recipient["resolved_to"],
        amount_eth=normalized_amount,
        chain_id=context.settings.demo_chain_id,
        requested_to=recipient["requested_to"],
        recipient_name=recipient["recipient_name"],
    )
    context.audit_store.append(
        "wallet_create_transfer_proposal",
        {
            "proposal_id": proposal.proposal_id,
            "requested_to": recipient["requested_to"],
            "resolved_to": recipient["resolved_to"],
            "recipient_name": recipient["recipient_name"],
            "amount": normalized_amount,
        },
    )
    if context.settings.demo_require_local_authorization:
        next_step = (
            "请先向用户展示 confirmation_preview 里的联系人名称、实际地址、金额和手续费；"
            "如果用户回复确认，请先调用 wallet_confirm_proposal；"
            "如果用户回复取消，请调用 wallet_cancel_proposal；"
            "确认后提案会推进到待本地授权状态。"
        )
    else:
        next_step = (
            "请先向用户展示 confirmation_preview 里的联系人名称、实际地址、金额和手续费；"
            "如果用户回复确认，请先调用 wallet_confirm_proposal；"
            "如果用户回复取消，请调用 wallet_cancel_proposal；"
            "只有确认成功后才能调用 wallet_execute_transfer。"
        )
    return {
        **dump_proposal(proposal),
        "quote": quote,
        "recipient_preview": recipient_preview,
        "confirmation_preview": confirmation_preview,
        "user_reply_actions": {
            "确认": "wallet_confirm_proposal",
            "取消": "wallet_cancel_proposal",
        },
        "assistant_confirmation_hint": (
            "先展示 confirmation_preview.confirmation_markdown；只有在用户明确回复确认后，才能调用 wallet_confirm_proposal。"
        ),
        "assistant_cancel_hint": (
            "如果用户明确回复取消，请调用 wallet_cancel_proposal，"
            "并传入当前 proposal_id，而不是继续确认或执行。"
        ),
        "assistant_reply_mapping_hint": (
            "用户回复“确认” -> wallet_confirm_proposal；"
            "用户回复“取消” -> wallet_cancel_proposal。"
        ),
        "next_step": next_step,
    }
