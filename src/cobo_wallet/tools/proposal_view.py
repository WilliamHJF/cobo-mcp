from __future__ import annotations

from datetime import UTC, datetime

from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_derived import (
    dump_proposal,
    get_estimated_total_cost_eth,
    get_execution_mode,
    get_requested_to,
)
from cobo_wallet.tools.preview import (
    build_confirmation_preview,
    build_recipient_preview,
)


TERMINAL_PROPOSAL_STATUSES = {"executed", "expired", "rejected"}
CANCELLABLE_PROPOSAL_STATUSES = {
    "pending",
    "confirmed_by_user",
    "awaiting_local_authorization",
    "authorized",
}


def _omit_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def refresh_proposal(context: ToolContext, proposal_id: str):
    proposal = context.proposal_store.get(proposal_id)
    if proposal is None:
        return None

    now = datetime.now(UTC)
    if (
        proposal.status not in TERMINAL_PROPOSAL_STATUSES
        and proposal.expires_at < now
    ):
        proposal = context.proposal_store.update_status(proposal_id, "expired")
    return proposal


def build_proposal_detail(context: ToolContext, proposal) -> dict:
    matched_by = _infer_matched_by(proposal)
    requested_to = get_requested_to(proposal)
    recipient_preview = build_recipient_preview(
        requested_to=requested_to,
        resolved_to=proposal.to,
        recipient_name=proposal.recipient_name,
        matched_by=matched_by,
    )
    confirmation_preview = _build_confirmation_preview(context, proposal, recipient_preview)
    whitelist_allowed = _is_whitelist_allowed(context, proposal)
    blocked_reason = _whitelist_blocked_reason(context, proposal)
    ready_for_execution = _is_ready_for_execution(context, proposal)
    cancellable = proposal.status in CANCELLABLE_PROPOSAL_STATUSES
    next_allowed_actions = _next_allowed_actions(context, proposal)
    user_reply_actions = _user_reply_actions(proposal)

    return _omit_none({
        **dump_proposal(proposal),
        "recipient_preview": recipient_preview,
        "confirmation_preview": confirmation_preview,
        "ready_for_execution": ready_for_execution,
        "cancellable": cancellable,
        "whitelist_required": (
            context.settings.demo_require_whitelist
            if context.settings.demo_require_whitelist
            else None
        ),
        "whitelist_allowed": (
            whitelist_allowed
            if context.settings.demo_require_whitelist
            else None
        ),
        "blocked_reason": blocked_reason,
        "next_allowed_actions": next_allowed_actions,
        "user_reply_actions": user_reply_actions,
        "message": _proposal_message(context, proposal),
    })


def _infer_matched_by(proposal) -> str:
    if proposal.recipient_name is None:
        return "address"
    if proposal.requested_to and proposal.requested_to.lower() != proposal.recipient_name.lower():
        return "alias"
    return "name"


def _build_confirmation_preview(context: ToolContext, proposal, recipient_preview: dict) -> dict | None:
    if proposal.status == "executed" and proposal.estimated_fee_eth:
        total_cost = get_estimated_total_cost_eth(proposal)
        return {
            "recipient_name": recipient_preview["recipient_name"],
            "requested_to": recipient_preview["requested_to"],
            "resolved_to": recipient_preview["resolved_to"],
            "display_text": recipient_preview["display_text"],
            "short_address": recipient_preview["short_address"],
            "amount_eth": proposal.amount_eth,
            "estimated_fee_eth": proposal.estimated_fee_eth,
            "estimated_total_cost_eth": total_cost,
            "review_items": [
                f"收款人: {recipient_preview['display_text']}",
                f"实际地址: {recipient_preview['resolved_to']}",
                f"转账金额: {proposal.amount_eth} ETH",
                f"实际成本: {total_cost} ETH",
                "状态: 已执行完成",
            ],
            "confirmation_card": {
                "title": "已执行转账",
                "fields": [
                    {"label": "收款人", "value": recipient_preview["display_text"]},
                    {"label": "实际地址", "value": recipient_preview["resolved_to"]},
                    {"label": "转账金额", "value": f"{proposal.amount_eth} ETH"},
                    {"label": "手续费", "value": f"{proposal.estimated_fee_eth} ETH"},
                    {"label": "总成本", "value": f"{total_cost} ETH"},
                    {"label": "状态", "value": "已执行完成"},
                ],
            },
            "confirmation_markdown": "\n".join(
                [
                    "这笔提案已经执行完成：",
                    "",
                    f"- 收款人：`{recipient_preview['display_text']}`",
                    f"- 实际地址：`{recipient_preview['resolved_to']}`",
                    f"- 转账金额：`{proposal.amount_eth} ETH`",
                    f"- 手续费：`{proposal.estimated_fee_eth} ETH`",
                    f"- 总成本：`{total_cost} ETH`",
                ]
            ),
        }

    if proposal.status in {"pending", "confirmed_by_user", "awaiting_local_authorization", "authorized"}:
        quote = context.wallet_service.estimate_transfer(
            to=proposal.to,
            amount_eth=proposal.amount_eth,
        )
        return build_confirmation_preview(
            recipient_preview=recipient_preview,
            amount_eth=proposal.amount_eth,
            estimated_fee_eth=quote["estimated_fee_eth"],
            estimated_total_cost_eth=quote["estimated_total_cost_eth"],
        )

    return None


def _is_ready_for_execution(context: ToolContext, proposal) -> bool:
    if not _is_whitelist_allowed(context, proposal):
        return False
    if context.settings.demo_require_local_authorization:
        return proposal.status == "authorized"
    return proposal.status == "confirmed_by_user"


def _next_allowed_actions(context: ToolContext, proposal) -> list[str]:
    if not _is_whitelist_allowed(context, proposal):
        if proposal.status in CANCELLABLE_PROPOSAL_STATUSES:
            return ["wallet_cancel_proposal"]
        if proposal.status == "executed":
            return ["wallet_get_transaction_status"]
        return []
    if proposal.status == "pending":
        return ["wallet_confirm_proposal", "wallet_cancel_proposal"]
    if proposal.status == "confirmed_by_user":
        actions = ["wallet_execute_transfer"]
        if proposal.status in CANCELLABLE_PROPOSAL_STATUSES:
            actions.append("wallet_cancel_proposal")
        return actions
    if proposal.status in {"awaiting_local_authorization", "authorized"}:
        return ["wallet_execute_transfer", "wallet_cancel_proposal"]
    if proposal.status == "executed":
        return ["wallet_get_transaction_status"]
    return []


def _user_reply_actions(proposal) -> dict:
    if proposal.status == "pending":
        return {"确认": "wallet_confirm_proposal", "取消": "wallet_cancel_proposal"}
    if proposal.status in {"confirmed_by_user", "awaiting_local_authorization", "authorized"}:
        return {"取消": "wallet_cancel_proposal"}
    return {}


def _proposal_message(context: ToolContext, proposal) -> str:
    blocked_reason = _whitelist_blocked_reason(context, proposal)
    if blocked_reason is not None:
        return blocked_reason
    if proposal.status == "pending":
        return "提案已创建，尚未记录用户确认。"
    if proposal.status == "confirmed_by_user":
        if context.settings.demo_require_local_authorization:
            return "提案已记录用户确认。执行时会先进入本地授权步骤。"
        return "提案已记录用户确认，现在可以执行。"
    if proposal.status == "awaiting_local_authorization":
        return "提案正在等待本地授权，授权完成后才能执行。"
    if proposal.status == "authorized":
        return "提案已完成本地授权，现在可以执行。"
    if proposal.status == "executed":
        if get_execution_mode(proposal) == "simulate":
            return "提案已执行完成，且这是一次本地模拟转账。"
        return "提案已执行完成。"
    if proposal.status == "rejected":
        return "提案已取消。"
    if proposal.status == "expired":
        return "提案已过期。"
    return f"提案当前状态为 {proposal.status}。"


def _is_whitelist_allowed(context: ToolContext, proposal) -> bool:
    return context.policy_engine.is_recipient_whitelisted(
        address=proposal.to,
        whitelist_store=context.whitelist_store,
    )


def _whitelist_blocked_reason(context: ToolContext, proposal) -> str | None:
    if not context.settings.demo_require_whitelist:
        return None
    if _is_whitelist_allowed(context, proposal):
        return None
    return (
        "收款地址当前不在白名单中，除非先恢复白名单允许，"
        "否则不能继续确认或执行这笔提案。"
    )
