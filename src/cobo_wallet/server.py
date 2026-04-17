from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cobo_wallet.config.env import get_settings
from cobo_wallet.policy.engine import PolicyEngine
from cobo_wallet.store.address_book import AddressBookStore
from cobo_wallet.store.audit import AuditStore
from cobo_wallet.store.proposals import ProposalStore
from cobo_wallet.tools import (
    add_recipient,
    cancel_proposal,
    confirm_proposal,
    create_transfer_proposal,
    delete_recipient,
    execute_transfer,
    get_proposal,
    get_overview,
    get_transaction_status,
    list_transactions,
    list_recipients,
    update_recipient,
)
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.wallet.service import WalletService


def build_context() -> ToolContext:
    settings = get_settings()
    return ToolContext(
        settings=settings,
        policy_engine=PolicyEngine(settings),
        address_book_store=AddressBookStore(settings),
        proposal_store=ProposalStore(settings),
        audit_store=AuditStore(settings),
        wallet_service=WalletService(settings),
    )


def build_server() -> FastMCP:
    context = build_context()
    mcp = FastMCP("cobo-wallet-mcp")

    @mcp.tool()
    def wallet_get_overview() -> dict:
        """返回钱包总览：账户、余额、策略和推荐调用流程。"""
        return get_overview.handle(context)

    @mcp.tool()
    def wallet_get_transaction_status(tx_hash: str) -> dict:
        return get_transaction_status.handle(context, tx_hash=tx_hash)

    @mcp.tool()
    def wallet_list_transactions(limit: int = 20) -> dict:
        """列出最近转账记录，包含已执行和已取消的提案，默认返回最近 20 条。"""
        return list_transactions.handle(context, limit=limit)

    @mcp.tool()
    def wallet_get_proposal(proposal_id: str) -> dict:
        """查看一条提案的当前状态、下一步可执行动作和确认信息。"""
        return get_proposal.handle(context, proposal_id=proposal_id)

    @mcp.tool()
    def wallet_cancel_proposal(proposal_id: str) -> dict:
        """取消一条尚未执行的提案。取消后，这条提案不能再继续确认或执行。"""
        return cancel_proposal.handle(context, proposal_id=proposal_id)

    @mcp.tool()
    def wallet_list_recipients() -> dict:
        """列出可用联系人名称、别名和实际地址，便于先选收款对象。"""
        return list_recipients.handle(context)

    @mcp.tool()
    def wallet_add_recipient(
        name: str,
        address: str,
        aliases: list[str] | None = None,
        note: str | None = None,
    ) -> dict:
        """新增一个收款人名称映射，之后转账时可以直接使用 name 或 aliases。"""
        return add_recipient.handle(
            context,
            name=name,
            address=address,
            aliases=aliases,
            note=note,
        )

    @mcp.tool()
    def wallet_update_recipient(
        name_or_alias: str,
        name: str | None = None,
        address: str | None = None,
        aliases: list[str] | None = None,
        note: str | None = None,
    ) -> dict:
        """更新已有收款人的名称、地址、别名或备注。name_or_alias 用来定位现有联系人。"""
        return update_recipient.handle(
            context,
            name_or_alias=name_or_alias,
            name=name,
            address=address,
            aliases=aliases,
            note=note,
        )

    @mcp.tool()
    def wallet_delete_recipient(name_or_alias: str) -> dict:
        """删除一个已有收款人。删除后，Codex 就不能再用这个名称或别名发起转账。"""
        return delete_recipient.handle(context, name_or_alias=name_or_alias)

    @mcp.tool()
    def wallet_prepare_transfer(to: str, amount: str) -> dict:
        """准备一笔转账。会解析联系人、检查余额、创建提案，并返回确认卡片。"""
        return create_transfer_proposal.handle(context, to=to, amount=amount)

    @mcp.tool()
    def wallet_confirm_proposal(proposal_id: str) -> dict:
        """记录用户已经在对话里明确确认这笔提案。只有这个步骤成功后，后续才允许执行转账。"""
        return confirm_proposal.handle(context, proposal_id=proposal_id)

    @mcp.tool()
    def wallet_execute_transfer(proposal_id: str) -> dict:
        """执行转账提案。默认模式下会直接执行；严格模式下会先返回本地授权指引。"""
        return execute_transfer.handle(context, proposal_id=proposal_id)

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
