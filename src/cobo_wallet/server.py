from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cobo_wallet.config.env import Settings, get_settings, reload_env_file
from cobo_wallet.policy.engine import PolicyEngine
from cobo_wallet.store.address_book import AddressBookStore
from cobo_wallet.store.audit import AuditStore
from cobo_wallet.store.proposals import ProposalStore
from cobo_wallet.store.whitelist import WhitelistStore
from cobo_wallet.tools import (
    cancel_proposal,
    check_request_capability,
    confirm_proposal,
    create_transfer_proposal,
    execute_transfer,
    get_proposal,
    get_overview,
    get_transaction_status,
    get_receive_card,
    list_whitelist,
    list_proposals,
    list_transactions,
    list_recipients,
)
from cobo_wallet.tools.context import ToolContext
from cobo_wallet.wallet.service import WalletService


def build_context(*, settings: Settings | None = None, reload_env: bool = False) -> ToolContext:
    if settings is not None:
        resolved_settings = settings
    elif reload_env:
        resolved_settings = reload_env_file()
    else:
        resolved_settings = get_settings()
    return ToolContext(
        settings=resolved_settings,
        policy_engine=PolicyEngine(resolved_settings),
        address_book_store=AddressBookStore(resolved_settings),
        whitelist_store=WhitelistStore(resolved_settings),
        proposal_store=ProposalStore(resolved_settings),
        audit_store=AuditStore(resolved_settings),
        wallet_service=WalletService(resolved_settings),
    )


def build_server() -> FastMCP:
    mcp = FastMCP("cobo-wallet-mcp")

    def runtime_context() -> ToolContext:
        # MCP 常驻进程需要在每次调用前刷新 .env，
        # 否则 Operator Console 修改后的限额、白名单开关等不会生效。
        return build_context(reload_env=True)

    @mcp.tool()
    def wallet_get_overview() -> dict:
        """返回钱包总览：账户、余额、策略和推荐调用流程。"""
        return get_overview.handle(runtime_context())

    @mcp.tool()
    def wallet_check_request_capability(request: str) -> dict:
        """钱包权限门卫。

        当用户提出任何钱包相关自然语言请求，尤其是你怀疑请求可能越权时，应优先先调用这个工具。
        - 如果返回 forbidden，你应直接使用 refusal_message 回复用户
        - 不要再尝试调用其他钱包工具绕过
        - 如果返回 allowed，再按 suggested_tool 继续
        """
        return check_request_capability.handle(runtime_context(), request=request)

    @mcp.tool()
    def wallet_get_transaction_status(tx_hash: str) -> dict:
        return get_transaction_status.handle(runtime_context(), tx_hash=tx_hash)

    @mcp.tool()
    def wallet_list_transactions(limit: int = 20) -> dict:
        """列出最近转账记录，包含已执行和已取消的提案，默认返回最近 20 条。"""
        return list_transactions.handle(runtime_context(), limit=limit)

    @mcp.tool()
    def wallet_list_proposals(
        limit: int = 20,
        statuses: list[str] | None = None,
    ) -> dict:
        """列出提案列表。默认优先展示未完成提案，也可以按 status 过滤。"""
        return list_proposals.handle(runtime_context(), limit=limit, statuses=statuses)

    @mcp.tool()
    def wallet_get_proposal(proposal_id: str) -> dict:
        """查看一条提案的当前状态、下一步可执行动作和确认信息。"""
        return get_proposal.handle(runtime_context(), proposal_id=proposal_id)

    @mcp.tool()
    def wallet_cancel_proposal(proposal_id: str) -> dict:
        """取消一条尚未执行的提案。取消后，这条提案不能再继续确认或执行。"""
        return cancel_proposal.handle(runtime_context(), proposal_id=proposal_id)

    @mcp.tool()
    def wallet_list_recipients() -> dict:
        """列出可用联系人名称、别名和实际地址，便于先选收款对象。"""
        return list_recipients.handle(runtime_context())

    @mcp.tool()
    def wallet_list_whitelist() -> dict:
        """列出当前白名单。开启白名单模式后，只允许向这些地址发起或执行转账。"""
        return list_whitelist.handle(runtime_context())

    @mcp.tool()
    def wallet_get_receive_card() -> dict:
        """返回当前钱包的收款信息，适合直接展示给用户或转发给他人。

        当用户表达以下意图时，应优先调用这个工具：
        - 显示我的收款信息
        - 把我的收款地址发给我
        - 生成一段可转发的收款文本
        - 生成收款名片
        - 别人怎么给我的钱包转账
        """
        return get_receive_card.handle(runtime_context())

    @mcp.tool()
    def wallet_prepare_transfer(to: str, amount: str) -> dict:
        """准备一笔转账。会解析联系人、检查白名单、检查余额、创建提案，并返回确认卡片。"""
        return create_transfer_proposal.handle(runtime_context(), to=to, amount=amount)

    @mcp.tool()
    def wallet_confirm_proposal(proposal_id: str) -> dict:
        """记录用户已经在对话里明确确认这笔提案。只有这个步骤成功后，后续才允许执行转账。"""
        return confirm_proposal.handle(runtime_context(), proposal_id=proposal_id)

    @mcp.tool()
    def wallet_execute_transfer(proposal_id: str) -> dict:
        """执行转账提案。默认模式下会直接执行；严格模式下会先返回本地授权指引。"""
        return execute_transfer.handle(runtime_context(), proposal_id=proposal_id)

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
