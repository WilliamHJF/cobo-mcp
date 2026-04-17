from __future__ import annotations

from web3 import HTTPProvider, Web3

from cobo_wallet.config.env import Settings


class RpcClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._web3 = Web3(HTTPProvider(settings.sepolia_rpc_url)) if settings.sepolia_rpc_url else None

    @property
    def web3(self) -> Web3:
        if self._web3 is None:
            raise RuntimeError("未配置 SEPOLIA_RPC_URL，无法访问链上数据")
        return self._web3

    def chain_id(self) -> int:
        return int(self.web3.eth.chain_id)
