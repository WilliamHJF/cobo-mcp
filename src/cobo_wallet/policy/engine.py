from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from cobo_wallet.config.env import Settings
from cobo_wallet.models import Proposal


class PolicyError(ValueError):
    """Raised when a request violates wallet policy."""


class PolicyEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def normalize_amount(self, amount_eth: str) -> str:
        raw = amount_eth.strip()
        normalized = re.sub(r"\s*eth\s*$", "", raw, flags=re.IGNORECASE).strip()
        if not normalized:
            raise PolicyError("转账金额不能为空")
        amount = self.validate_amount(normalized)
        return format(amount, "f")

    def validate_chain_id(self, chain_id: int) -> None:
        if chain_id != self.settings.demo_chain_id:
            raise PolicyError(f"仅允许使用 Sepolia 链，当前 chain_id={chain_id}")

    def validate_amount(self, amount_eth: str) -> Decimal:
        try:
            amount = Decimal(amount_eth)
        except InvalidOperation as exc:
            raise PolicyError("转账金额格式不正确") from exc

        if amount <= 0:
            raise PolicyError("转账金额必须大于 0")

        if amount > Decimal(self.settings.demo_max_transfer_eth):
            raise PolicyError(
                f"单笔转账金额不能超过 {self.settings.demo_max_transfer_eth} ETH"
            )
        return amount

    def validate_write_enabled(self) -> None:
        if not self.settings.demo_write_enabled:
            raise PolicyError("当前项目处于只读模式，未开启写入权限")

    def is_recipient_whitelisted(self, *, address: str, whitelist_store) -> bool:
        if not self.settings.demo_require_whitelist:
            return True
        return whitelist_store.is_allowed(address)

    def validate_recipient_whitelisted(
        self,
        *,
        address: str,
        whitelist_store,
        requested_to: str | None = None,
        recipient_name: str | None = None,
    ) -> None:
        if self.is_recipient_whitelisted(
            address=address,
            whitelist_store=whitelist_store,
        ):
            return

        target_display = recipient_name or requested_to or address
        raise PolicyError(
            "收款地址当前不在白名单中，不能发起或执行这笔转账。"
            f"目标: {target_display} ({address})。"
            "请先调用 wallet_allow_recipient 将该地址加入白名单。"
        )

    def validate_proposal_executable(self, proposal: Proposal) -> None:
        self.validate_chain_id(proposal.chain_id)
        if self.settings.demo_require_local_authorization and proposal.status != "authorized":
            raise PolicyError("提案尚未完成本地授权，不能执行")
        if not self.settings.demo_require_local_authorization and proposal.status != "confirmed_by_user":
            raise PolicyError("提案尚未记录用户确认，不能执行")
