from __future__ import annotations

from decimal import Decimal

from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_derived import (
    get_balance_after_eth,
    get_estimated_total_cost_eth,
    get_execution_message,
    get_execution_mode,
    get_explorer_url,
    get_happened_at,
    get_requested_to,
)


def _short_address(address: str) -> str:
    if len(address) < 12:
        return address
    return f"{address[:6]}...{address[-4:]}"


def _status_display(status: str) -> str:
    mapping = {
        "executed": "已执行",
        "rejected": "已取消",
        "expired": "已过期",
        "pending": "待确认",
    }
    return mapping.get(status, status)


def _omit_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _build_transaction_item(proposal) -> dict:
    recipient_display = (
        f"{proposal.recipient_name} <{proposal.to}>"
        if proposal.recipient_name
        else proposal.to
    )
    is_executed = proposal.status == "executed"
    execution_mode = get_execution_mode(proposal)
    happened_at = get_happened_at(proposal)
    record_type = "executed" if is_executed else "cancelled"
    message = get_execution_message(proposal)
    return _omit_none({
        "tx_hash": proposal.tx_hash,
        "proposal_id": proposal.proposal_id,
        "record_type": record_type,
        "status": proposal.status,
        "status_display": _status_display(proposal.status),
        "execution_mode": execution_mode,
        "simulated": execution_mode == "simulate",
        "requested_to": get_requested_to(proposal),
        "recipient_name": proposal.recipient_name,
        "recipient_display": recipient_display,
        "short_address": _short_address(proposal.to),
        "to": proposal.to,
        "amount_eth": proposal.amount_eth,
        "estimated_fee_eth": proposal.estimated_fee_eth,
        "estimated_total_cost_eth": get_estimated_total_cost_eth(proposal),
        "balance_before_eth": proposal.balance_before_eth,
        "balance_after_eth": get_balance_after_eth(proposal),
        "created_at": proposal.created_at.isoformat(),
        "executed_at": proposal.executed_at.isoformat() if proposal.executed_at else None,
        "canceled_at": proposal.canceled_at.isoformat() if proposal.canceled_at else None,
        "happened_at": happened_at.isoformat(),
        "explorer_url": get_explorer_url(proposal),
        "message": message,
    })


def handle(context: ToolContext, limit: int = 20) -> dict:
    if limit <= 0:
        raise PolicyError("limit 必须大于 0")

    proposals = context.proposal_store.list_history()
    selected = proposals[:limit]
    transactions = [_build_transaction_item(proposal) for proposal in selected]

    total_record_amount = Decimal("0")
    executed_amount = Decimal("0")
    cancelled_amount = Decimal("0")
    simulated_count = 0
    executed_count = 0
    cancelled_count = 0
    for item in transactions:
        amount = Decimal(item["amount_eth"])
        total_record_amount += amount
        if item["simulated"]:
            simulated_count += 1
        if item["record_type"] == "executed":
            executed_count += 1
            executed_amount += amount
        if item["record_type"] == "cancelled":
            cancelled_count += 1
            cancelled_amount += amount

    result = {
        "count": len(transactions),
        "limit": limit,
        "total_history_count": len(proposals),
        "transactions": transactions,
        "summary": {
            "displayed_total_record_amount_eth": format(total_record_amount, "f"),
            "displayed_executed_amount_eth": format(executed_amount, "f"),
            "displayed_cancelled_amount_eth": format(cancelled_amount, "f"),
            "simulated_count": simulated_count,
            "executed_count": executed_count,
            "cancelled_count": cancelled_count,
            "latest_happened_at": (
                transactions[0]["happened_at"] if transactions else None
            ),
        },
        "message": (
            "返回最近转账记录，包含已执行和已取消的提案。"
            if transactions
            else "当前还没有转账记录。"
        ),
    }
    context.audit_store.append(
        "wallet_list_transactions",
        {"count": len(transactions), "limit": limit},
    )
    return result
