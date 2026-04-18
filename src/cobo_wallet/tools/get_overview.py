from __future__ import annotations

from cobo_wallet.amounts import format_eth_display
from cobo_wallet.tools.context import ToolContext


def handle(context: ToolContext) -> dict:
    account = context.wallet_service.get_account_summary()
    balance = context.wallet_service.get_balance()
    balance_source_info = context.wallet_service.get_balance_source_info()
    recommended_flow = ["wallet_list_recipients"]
    if context.settings.demo_require_whitelist:
        recommended_flow.append("wallet_list_whitelist")
    recommended_flow.extend(
        [
            "wallet_prepare_transfer",
            "wallet_confirm_proposal",
            "wallet_execute_transfer",
            "wallet_get_transaction_status",
        ]
    )
    policy = {
        "chain_id": context.settings.demo_chain_id,
        "write_enabled": context.settings.demo_write_enabled,
        "execution_mode": context.settings.demo_execution_mode,
        "max_transfer_eth": format_eth_display(context.settings.demo_max_transfer_eth),
        "proposal_ttl_minutes": context.settings.demo_proposal_ttl_minutes,
        "local_authorization_required": context.settings.demo_require_local_authorization,
        "whitelist_required": context.settings.demo_require_whitelist,
    }
    recipients = context.address_book_store.list()
    whitelist_entries = context.whitelist_store.list()
    result = {
        "account": account,
        "balance": balance,
        "state_management": balance_source_info,
        "policy": policy,
        "recipient_count": len(recipients),
        "whitelist_count": len(whitelist_entries),
        "recommended_flow": recommended_flow,
        "receive_tools": ["wallet_get_receive_card"],
        "whitelist_tools": ["wallet_list_whitelist"],
        "history_tools": ["wallet_list_transactions"],
        "proposal_tools": [
            "wallet_list_proposals",
            "wallet_get_proposal",
            "wallet_cancel_proposal",
        ],
        "agent_allowed_write_areas": [
            "创建转账提案",
            "确认提案",
            "取消提案",
            "执行转账",
            "更新提案状态与交易记录",
        ],
        "agent_forbidden_write_areas": [
            "钱包私钥与 RPC 配置修改",
            "模拟余额人工调整",
            "白名单修改",
            "地址簿修改",
            "策略与权限开关修改",
        ],
        "runtime_execution_switches": {
            "write_enabled": context.settings.demo_write_enabled,
            "execution_mode": context.settings.demo_execution_mode,
            "explanation": (
                "这些开关会影响转账流程是否能真正执行，"
                "但它们不改变 Agent 对转账主流程本身的权限边界。"
            ),
        },
        "guardrail_tool": "wallet_check_request_capability",
        "guardrail_policy": (
            "当用户提出钱包相关自然语言请求，尤其是你怀疑请求可能越权时，"
            "应优先先调用 wallet_check_request_capability。"
            "如果它返回 forbidden，应直接使用 refusal_message 回复用户，"
            "不要尝试通过其他钱包工具绕过。"
        ),
        "operator_console_command": "uv run cobo-wallet-operator",
        "operator_only_areas": [
            "钱包私钥与 RPC 配置",
            "模拟余额调整",
            "白名单修改",
            "地址簿修改",
            "策略与权限开关",
        ],
        "operator_console_hint": (
            "敏感配置和管理类修改不再通过 MCP 提供。"
            "如需修改白名单、地址簿、模拟余额或钱包配置，请使用本地 Operator Console。"
        ),
    }
    context.audit_store.append(
        "wallet_get_overview",
        {
            "recipient_count": len(recipients),
            "whitelist_count": len(whitelist_entries),
            "balance_source": balance_source_info["balance_source"],
        },
    )
    return result
