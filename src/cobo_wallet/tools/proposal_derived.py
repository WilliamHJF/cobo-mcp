from __future__ import annotations

from decimal import Decimal


def _format_decimal(value: Decimal) -> str:
    return format(value, "f")


def get_requested_to(proposal) -> str:
    return proposal.requested_to or proposal.to


def get_execution_mode(proposal) -> str | None:
    if not proposal.tx_hash:
        return None
    if proposal.tx_hash.startswith("sim_"):
        return "simulate"
    return "sepolia"


def get_estimated_total_cost_eth(proposal) -> str | None:
    if proposal.estimated_fee_eth is None:
        return None
    return _format_decimal(Decimal(proposal.amount_eth) + Decimal(proposal.estimated_fee_eth))


def get_balance_after_eth(proposal) -> str | None:
    total_cost = get_estimated_total_cost_eth(proposal)
    if proposal.balance_before_eth is None or total_cost is None:
        return None
    return _format_decimal(Decimal(proposal.balance_before_eth) - Decimal(total_cost))


def get_explorer_url(proposal) -> str | None:
    mode = get_execution_mode(proposal)
    if not proposal.tx_hash or mode == "simulate":
        return None
    if proposal.chain_id == 11155111:
        return f"https://sepolia.etherscan.io/tx/{proposal.tx_hash}"
    return None


def get_execution_message(proposal) -> str | None:
    if proposal.status == "executed":
        if get_execution_mode(proposal) == "simulate":
            return "本地模拟执行成功，未向真实区块链广播交易"
        return "交易已执行完成。"
    if proposal.status == "rejected":
        return "这条转账提案后来被取消，没有进入实际执行。"
    return None


def get_happened_at(proposal):
    return (
        proposal.executed_at
        or proposal.canceled_at
        or proposal.user_confirmed_at
        or proposal.created_at
    )


def dump_proposal(proposal) -> dict:
    data = proposal.model_dump(mode="json", exclude_none=True)
    execution_mode = get_execution_mode(proposal)
    if execution_mode is not None:
        data["execution_mode"] = execution_mode

    total_cost = get_estimated_total_cost_eth(proposal)
    if total_cost is not None:
        data["estimated_total_cost_eth"] = total_cost

    balance_after = get_balance_after_eth(proposal)
    if balance_after is not None:
        data["balance_after_eth"] = balance_after

    explorer_url = get_explorer_url(proposal)
    if explorer_url is not None:
        data["explorer_url"] = explorer_url

    execution_message = get_execution_message(proposal)
    if execution_message is not None:
        data["execution_message"] = execution_message

    if "requested_to" not in data:
        data["requested_to"] = get_requested_to(proposal)

    return data
