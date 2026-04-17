from __future__ import annotations

from cobo_wallet.tools.context import ToolContext
from cobo_wallet.tools.proposal_derived import (
    get_balance_after_eth,
    get_estimated_total_cost_eth,
    get_execution_mode,
    get_explorer_url,
    get_requested_to,
)


def _omit_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def handle(context: ToolContext, tx_hash: str) -> dict:
    simulated = context.proposal_store.get_by_tx_hash(tx_hash)
    if simulated is not None:
        result = _omit_none({
            "tx_hash": tx_hash,
            "status": "confirmed" if simulated.status == "executed" else simulated.status,
            "execution_mode": get_execution_mode(simulated) or "simulate",
            "simulated": (get_execution_mode(simulated) or "simulate") == "simulate",
            "proposal_id": simulated.proposal_id,
            "requested_to": get_requested_to(simulated),
            "recipient_name": simulated.recipient_name,
            "to": simulated.to,
            "amount_eth": simulated.amount_eth,
            "estimated_fee_eth": simulated.estimated_fee_eth,
            "estimated_total_cost_eth": get_estimated_total_cost_eth(simulated),
            "balance_before_eth": simulated.balance_before_eth,
            "balance_after_eth": get_balance_after_eth(simulated),
            "executed_at": (
                simulated.executed_at.isoformat()
                if simulated.executed_at is not None
                else None
            ),
            "explorer_url": get_explorer_url(simulated),
            "message": "这是一笔本地模拟交易，没有真实广播到 Sepolia 链上",
        })
        context.audit_store.append("wallet_get_transaction_status", {"tx_hash": tx_hash})
        return result

    result = context.wallet_service.get_transaction_status(tx_hash)
    context.audit_store.append("wallet_get_transaction_status", {"tx_hash": tx_hash})
    return result
