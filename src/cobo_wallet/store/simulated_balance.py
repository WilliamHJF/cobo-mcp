from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from cobo_wallet.config.env import Settings
from cobo_wallet.store.common import read_json, write_json


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class SimulatedBalanceStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.demo_data_dir) / "simulated_balance.json"

    def get_balance_eth(self) -> Decimal:
        raw = read_json(self.path, default=None)
        if raw is None:
            balance = Decimal(self.settings.demo_simulated_balance_eth)
            self.set_balance_eth(balance)
            return balance
        return Decimal(str(raw.get("balance_eth", self.settings.demo_simulated_balance_eth)))

    def set_balance_eth(self, balance_eth: Decimal) -> None:
        write_json(self.path, {"balance_eth": _format_decimal(balance_eth)})

    def debit(self, amount_eth: Decimal) -> tuple[Decimal, Decimal]:
        balance_before = self.get_balance_eth()
        if amount_eth > balance_before:
            raise RuntimeError(
                "本地模拟余额不足，"
                f"当前余额 {_format_decimal(balance_before)} ETH，"
                f"需要 {_format_decimal(amount_eth)} ETH"
            )
        balance_after = balance_before - amount_eth
        self.set_balance_eth(balance_after)
        return balance_before, balance_after
