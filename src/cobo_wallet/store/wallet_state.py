from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from cobo_wallet.config.env import Settings
from cobo_wallet.models import WalletState
from cobo_wallet.store.common import read_json, write_json


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class WalletStateStore:
    def __init__(self, settings: Settings, *, signer) -> None:
        self.settings = settings
        self.signer = signer
        self.path = Path(settings.demo_data_dir) / "wallet_state.json"
        self.legacy_simulated_balance_path = (
            Path(settings.demo_data_dir) / "simulated_balance.json"
        )

    def get_state(self) -> WalletState:
        raw = read_json(self.path, default=None)
        if raw is None:
            state = self._build_initial_state()
            self.save_state(state)
            return state

        state = WalletState.model_validate(self._normalize_raw(raw))
        synced = self._sync_runtime_metadata(state)
        if synced != state:
            self.save_state(synced)
        return synced

    def save_state(self, state: WalletState) -> None:
        write_json(self.path, state.model_dump(mode="json"))

    def get_balance_eth(self) -> Decimal:
        return Decimal(self.get_state().simulated_balance_eth)

    def set_balance_eth(self, balance_eth: Decimal) -> WalletState:
        state = self.get_state().model_copy(
            update={"simulated_balance_eth": _format_decimal(balance_eth)}
        )
        self.save_state(state)
        return state

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

    def _build_initial_state(self) -> WalletState:
        metadata = self._runtime_metadata()
        initial_balance = self._load_initial_balance_eth()
        return WalletState(
            **metadata,
            simulated_balance_eth=_format_decimal(initial_balance),
        )

    def _normalize_raw(self, raw: dict) -> dict:
        metadata = self._runtime_metadata()
        normalized = dict(raw)
        for key, value in metadata.items():
            normalized.setdefault(key, value)
        normalized.setdefault(
            "simulated_balance_eth",
            _format_decimal(self._load_initial_balance_eth()),
        )
        return normalized

    def _load_initial_balance_eth(self) -> Decimal:
        legacy = read_json(self.legacy_simulated_balance_path, default=None)
        if legacy is not None:
            return Decimal(
                str(legacy.get("balance_eth", self.settings.demo_simulated_balance_eth))
            )
        return Decimal(self.settings.demo_simulated_balance_eth)

    def _runtime_metadata(self) -> dict:
        return {
            "address": self.signer.address(),
            "network": "Ethereum Sepolia",
            "chain_id": self.settings.demo_chain_id,
            "execution_mode": self.settings.demo_execution_mode,
            "configured": self.settings.is_wallet_configured,
            "write_enabled": self.settings.demo_write_enabled,
        }

    def _sync_runtime_metadata(self, state: WalletState) -> WalletState:
        metadata = self._runtime_metadata()
        wallet_identity_changed = (
            state.address != metadata["address"]
            or state.chain_id != metadata["chain_id"]
            or state.network != metadata["network"]
        )

        updates = dict(metadata)
        if wallet_identity_changed:
            updates["simulated_balance_eth"] = _format_decimal(
                Decimal(self.settings.demo_simulated_balance_eth)
            )
        return state.model_copy(update=updates)
