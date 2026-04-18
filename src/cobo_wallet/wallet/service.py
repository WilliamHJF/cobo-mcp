from __future__ import annotations

import hashlib
from decimal import Decimal

from web3 import Web3

from cobo_wallet.amounts import format_eth_display
from cobo_wallet.config.env import Settings
from cobo_wallet.store.wallet_state import WalletStateStore
from cobo_wallet.wallet.rpc import RpcClient
from cobo_wallet.wallet.signer import Signer


class WalletService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rpc = RpcClient(settings)
        self.signer = Signer(settings)
        self.wallet_state_store = WalletStateStore(settings, signer=self.signer)

    def get_account_summary(self) -> dict:
        state = self.wallet_state_store.get_state()
        return {
            "address": state.address,
            "network": state.network,
            "chain_id": state.chain_id,
            "write_enabled": state.write_enabled,
            "execution_mode": state.execution_mode,
            "configured": state.configured,
        }

    def get_balance_source_info(self) -> dict:
        if self.settings.demo_execution_mode == "simulate":
            return {
                "balance_source": "wallet_state",
                "state_managed": True,
                "wallet_state_path": str(self.wallet_state_store.path.resolve()),
                "initial_balance_env": "DEMO_SIMULATED_BALANCE_ETH",
            }
        return {
            "balance_source": "chain_rpc",
            "state_managed": False,
            "wallet_state_path": None,
            "initial_balance_env": None,
        }

    def get_balance(self) -> dict:
        if self.settings.demo_execution_mode == "simulate":
            state = self.wallet_state_store.get_state()
            result = {
                "address": state.address,
                "balance_eth": format_eth_display(state.simulated_balance_eth),
                "configured": state.configured,
                "execution_mode": "simulate",
                "simulated": True,
            }
            result.update(self.get_balance_source_info())
            return result
        if not self.settings.is_wallet_configured:
            result = {
                "address": self.signer.address(),
                "balance_eth": "0",
                "configured": False,
            }
            result.update(self.get_balance_source_info())
            return result
        address = self.signer.address()
        balance_wei = self.rpc.web3.eth.get_balance(address)
        balance_eth = format_eth_display(Web3.from_wei(balance_wei, "ether"))
        result = {"address": address, "balance_eth": balance_eth, "configured": True}
        result.update(self.get_balance_source_info())
        return result

    def get_balance_eth_decimal(self) -> Decimal:
        if self.settings.demo_execution_mode == "simulate":
            return self.wallet_state_store.get_balance_eth()
        if not self.settings.is_wallet_configured:
            return Decimal("0")
        address = self.signer.address()
        balance_wei = self.rpc.web3.eth.get_balance(address)
        return Decimal(str(Web3.from_wei(balance_wei, "ether")))

    def build_balance_check(
        self,
        *,
        amount_eth: Decimal,
        estimated_fee_eth: Decimal,
    ) -> dict:
        current_balance = self.get_balance_eth_decimal()
        required_total = amount_eth + estimated_fee_eth
        remaining = current_balance - required_total
        result = {
            "current_balance_eth": format_eth_display(current_balance),
            "required_total_eth": format_eth_display(required_total),
            "balance_sufficient": current_balance >= required_total,
            "remaining_balance_after_transfer_eth": format_eth_display(remaining),
        }
        result.update(self.get_balance_source_info())
        return result

    def _estimate_transfer_values(self, amount_eth: str) -> dict:
        amount = Decimal(amount_eth)
        gas_estimate = 21000
        gas_price_wei = 0
        if self.settings.is_wallet_configured:
            gas_price_wei = int(self.rpc.web3.eth.gas_price)
        fee_eth = Decimal(str(Web3.from_wei(gas_estimate * gas_price_wei, "ether")))
        return {
            "amount_eth": amount,
            "estimated_gas": gas_estimate,
            "estimated_fee_eth": fee_eth,
            "estimated_total_cost_eth": amount + fee_eth,
        }

    def estimate_transfer(self, to: str, amount_eth: str) -> dict:
        values = self._estimate_transfer_values(amount_eth)
        result = {
            "to": to,
            "amount_eth": format_eth_display(values["amount_eth"]),
            "estimated_gas": values["estimated_gas"],
            "estimated_fee_eth": format_eth_display(values["estimated_fee_eth"]),
            "estimated_total_cost_eth": format_eth_display(
                values["estimated_total_cost_eth"]
            ),
        }
        result.update(
            self.build_balance_check(
                amount_eth=values["amount_eth"],
                estimated_fee_eth=values["estimated_fee_eth"],
            )
        )
        return result

    def get_transaction_status(self, tx_hash: str) -> dict:
        if not self.settings.is_wallet_configured:
            return {"tx_hash": tx_hash, "status": "unknown", "message": "钱包尚未配置"}
        receipt = self.rpc.web3.eth.get_transaction_receipt(tx_hash)
        return {
            "tx_hash": tx_hash,
            "status": "confirmed" if receipt["status"] == 1 else "failed",
            "block_number": receipt["blockNumber"],
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}",
        }

    def confirm_and_send(self, proposal) -> dict:
        if not self.settings.demo_write_enabled:
            raise RuntimeError(
                "当前项目处于只读模式，不能发送交易。"
                "请先在本地 Operator Console 的 Policy 页面开启“允许写入”。"
            )
        if self.settings.demo_execution_mode == "simulate":
            quote_values = self._estimate_transfer_values(proposal.amount_eth)
            total_cost_eth = quote_values["estimated_total_cost_eth"]
            balance_before, balance_after = self.wallet_state_store.debit(total_cost_eth)
            raw = f"{proposal.proposal_id}|{proposal.intent_hash}|simulate"
            simulated_tx_hash = "sim_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
            return {
                "tx_hash": simulated_tx_hash,
                "status": "confirmed",
                "execution_mode": "simulate",
                "simulated": True,
                "proposal_id": proposal.proposal_id,
                "requested_to": proposal.requested_to,
                "recipient_name": proposal.recipient_name,
                "to": proposal.to,
                "amount_eth": format_eth_display(proposal.amount_eth),
                "estimated_fee_eth": format_eth_display(
                    quote_values["estimated_fee_eth"]
                ),
                "estimated_total_cost_eth": format_eth_display(total_cost_eth),
                "balance_before_eth": format_eth_display(balance_before),
                "balance_after_eth": format_eth_display(balance_after),
                "message": "本地模拟执行成功，未向真实区块链广播交易",
                "explorer_url": None,
            }

        raise NotImplementedError("当前版本尚未接入真实链上签名与广播")
