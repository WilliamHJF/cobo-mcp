from __future__ import annotations

from eth_account import Account

from cobo_wallet.config.env import Settings


class Signer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def address(self) -> str:
        if not self.settings.demo_private_key:
            return "UNCONFIGURED"
        return Account.from_key(self.settings.demo_private_key).address
