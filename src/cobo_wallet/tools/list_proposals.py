from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_derived import (
    dump_proposal,
    get_happened_at,
)


ACTIVE_PROPOSAL_STATUSES = {
    "pending",
    "confirmed_by_user",
    "awaiting_local_authorization",
    "authorized",
}
TERMINAL_PROPOSAL_STATUSES = {"executed", "expired", "rejected"}
ALL_PROPOSAL_STATUSES = ACTIVE_PROPOSAL_STATUSES | TERMINAL_PROPOSAL_STATUSES
CANCELLABLE_PROPOSAL_STATUSES = {
    "pending",
    "confirmed_by_user",
    "awaiting_local_authorization",
    "authorized",
}


def _status_display(status: str) -> str:
    mapping = {
        "pending": "待确认",
        "confirmed_by_user": "已确认待执行",
        "awaiting_local_authorization": "待本地授权",
        "authorized": "已授权待执行",
        "executed": "已执行",
        "expired": "已过期",
        "rejected": "已取消",
    }
    return mapping.get(status, status)


def _omit_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _normalize_statuses(statuses: list[str] | None) -> list[str] | None:
    if statuses is None:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for status in statuses:
        value = status.strip()
        if not value:
            raise PolicyError("status 不能为空")
        if value not in ALL_PROPOSAL_STATUSES:
            allowed = ", ".join(sorted(ALL_PROPOSAL_STATUSES))
            raise PolicyError(f"不支持的 status: {value}。允许值: {allowed}")
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _refresh_proposal(context: ToolContext, proposal):
    now = datetime.now(UTC)
    if proposal.status in TERMINAL_PROPOSAL_STATUSES:
        return proposal
    if proposal.expires_at >= now:
        return proposal
    return context.proposal_store.update_status(proposal.proposal_id, "expired")


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


def _build_proposal_item(context: ToolContext, proposal) -> dict:
    whitelist_allowed = _is_whitelist_allowed(context, proposal)
    blocked_reason = _whitelist_blocked_reason(context, proposal)
    return _omit_none({
        **dump_proposal(proposal),
        "status_display": _status_display(proposal.status),
        "is_terminal": proposal.status in TERMINAL_PROPOSAL_STATUSES,
        "ready_for_execution": _is_ready_for_execution(context, proposal),
        "cancellable": proposal.status in CANCELLABLE_PROPOSAL_STATUSES,
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
        "next_allowed_actions": _next_allowed_actions(context, proposal),
        "happened_at": (
            get_happened_at(proposal).isoformat()
            if proposal.status in TERMINAL_PROPOSAL_STATUSES
            else None
        ),
    })


def handle(
    context: ToolContext,
    limit: int = 20,
    statuses: list[str] | None = None,
) -> dict:
    if limit <= 0:
        raise PolicyError("limit 必须大于 0")

    normalized_statuses = _normalize_statuses(statuses)
    proposals = [
        _refresh_proposal(context, proposal)
        for proposal in context.proposal_store.list()
    ]
    if normalized_statuses is not None:
        proposals = [
            proposal
            for proposal in proposals
            if proposal.status in normalized_statuses
        ]

    active_proposals = [
        proposal for proposal in proposals if proposal.status in ACTIVE_PROPOSAL_STATUSES
    ]
    terminal_proposals = [
        proposal for proposal in proposals if proposal.status in TERMINAL_PROPOSAL_STATUSES
    ]
    active_proposals.sort(key=lambda proposal: proposal.created_at, reverse=True)
    terminal_proposals.sort(key=get_happened_at, reverse=True)

    ordered = active_proposals + terminal_proposals
    selected = ordered[:limit]
    proposal_items = [
        _build_proposal_item(context, proposal)
        for proposal in selected
    ]
    status_summary = dict(
        sorted(Counter(proposal.status for proposal in proposals).items())
    )

    result = {
        "count": len(proposal_items),
        "limit": limit,
        "total_matching_count": len(ordered),
        "unfinished_first": True,
        "status_filter": normalized_statuses,
        "status_summary": status_summary,
        "proposals": proposal_items,
        "message": (
            "返回提案列表，默认优先展示未完成提案。"
            if proposal_items
            else "当前没有匹配的提案。"
        ),
    }
    context.audit_store.append(
        "wallet_list_proposals",
        {
            "count": len(proposal_items),
            "limit": limit,
            "statuses": normalized_statuses,
        },
    )
    return _omit_none(result)


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
    return "收款地址当前不在白名单中，暂时不能继续确认或执行。"
