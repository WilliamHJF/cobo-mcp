from __future__ import annotations

import hashlib
from decimal import Decimal

from web3 import Web3

from cobo_wallet.config.env import Settings
from cobo_wallet.store.simulated_balance import SimulatedBalanceStore
from cobo_wallet.wallet.rpc import RpcClient
from cobo_wallet.wallet.signer import Signer


class WalletService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rpc = RpcClient(settings)
        self.signer = Signer(settings)
        self.simulated_balance_store = SimulatedBalanceStore(settings)

    def get_account_summary(self) -> dict:
        return {
            "address": self.signer.address(),
            "network": "Ethereum Sepolia",
            "chain_id": self.settings.demo_chain_id,
            "write_enabled": self.settings.demo_write_enabled,
            "execution_mode": self.settings.demo_execution_mode,
            "configured": self.settings.is_wallet_configured,
        }

    def get_balance(self) -> dict:
        if self.settings.demo_execution_mode == "simulate":
            balance_eth = self.simulated_balance_store.get_balance_eth()
            return {
                "address": self.signer.address(),
                "balance_eth": str(balance_eth),
                "configured": self.settings.is_wallet_configured,
                "execution_mode": "simulate",
                "simulated": True,
            }
        if not self.settings.is_wallet_configured:
            return {"address": self.signer.address(), "balance_eth": "0", "configured": False}
        address = self.signer.address()
        balance_wei = self.rpc.web3.eth.get_balance(address)
        balance_eth = str(Web3.from_wei(balance_wei, "ether"))
        return {"address": address, "balance_eth": balance_eth, "configured": True}

    def get_balance_eth_decimal(self) -> Decimal:
        if self.settings.demo_execution_mode == "simulate":
            return self.simulated_balance_store.get_balance_eth()
        if not self.settings.is_wallet_configured:
            return Decimal("0")
        address = self.signer.address()
        balance_wei = self.rpc.web3.eth.get_balance(address)
        return Decimal(str(Web3.from_wei(balance_wei, "ether")))

    def build_balance_check(self, *, amount_eth: str, estimated_fee_eth: str) -> dict:
        current_balance = self.get_balance_eth_decimal()
        required_total = Decimal(amount_eth) + Decimal(estimated_fee_eth)
        remaining = current_balance - required_total
        return {
            "current_balance_eth": str(current_balance),
            "required_total_eth": str(required_total),
            "balance_sufficient": current_balance >= required_total,
            "remaining_balance_after_transfer_eth": str(remaining),
        }

    def estimate_transfer(self, to: str, amount_eth: str) -> dict:
        if not self.settings.is_wallet_configured:
            gas_estimate = 21000
            gas_price_wei = 0
        else:
            gas_estimate = 21000
            gas_price_wei = int(self.rpc.web3.eth.gas_price)
        fee_eth = str(Web3.from_wei(gas_estimate * gas_price_wei, "ether"))
        total_cost_eth = str(Decimal(amount_eth) + Decimal(fee_eth))
        result = {
            "to": to,
            "amount_eth": amount_eth,
            "estimated_gas": gas_estimate,
            "estimated_fee_eth": fee_eth,
            "estimated_total_cost_eth": total_cost_eth,
        }
        result.update(
            self.build_balance_check(
                amount_eth=amount_eth,
                estimated_fee_eth=fee_eth,
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
            raise RuntimeError("当前处于只读模式，不能发送交易")
        if self.settings.demo_execution_mode == "simulate":
            quote = self.estimate_transfer(to=proposal.to, amount_eth=proposal.amount_eth)
            total_cost_eth = Decimal(quote["estimated_total_cost_eth"])
            balance_before, balance_after = self.simulated_balance_store.debit(total_cost_eth)
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
                "amount_eth": proposal.amount_eth,
                "estimated_fee_eth": quote["estimated_fee_eth"],
                "estimated_total_cost_eth": quote["estimated_total_cost_eth"],
                "balance_before_eth": str(balance_before),
                "balance_after_eth": str(balance_after),
                "message": "本地模拟执行成功，未向真实区块链广播交易",
                "explorer_url": None,
            }

        raise NotImplementedError("当前版本尚未接入真实链上签名与广播")
