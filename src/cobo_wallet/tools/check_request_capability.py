from __future__ import annotations

import re

from cobo_wallet.tools.context import ToolContext


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _match_proposal_id(text: str) -> str | None:
    match = re.search(r"\bproposal_[0-9a-f]{8}\b", text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _match_tx_hash(text: str) -> str | None:
    match = re.search(r"\b(sim_[0-9a-f]{16,}|0x[0-9a-f]{16,})\b", text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _matches_balance_adjustment_intent(raw: str, normalized: str) -> bool:
    patterns = [
        r"余额\s*[加减]\s*\d+(\.\d+)?\s*(eth|usdt|btc)",
        r"给.*余额\s*[加减]\s*\d+(\.\d+)?\s*(eth|usdt|btc)",
        r"把.*余额\s*(改成|设成|调成|变成)\s*\d+(\.\d+)?\s*(eth|usdt|btc)",
        r"(给|把).*(钱包|账户).*[加减]\s*\d+(\.\d+)?\s*(eth|usdt|btc).*(测试)?",
        r"(top up|add|increase|decrease|reduce).*(wallet|balance|fund).*\d+(\.\d+)?\s*(eth|usdt|btc)",
    ]
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns)


def _operator_only_response(
    *,
    request: str,
    category: str,
    area: str,
    page: str,
    matched_rules: list[str],
) -> dict:
    refusal_message = (
        f"这个请求超出当前 Agent 的 MCP 权限范围，我不能直接执行。"
        f"{area} 目前只允许人工在本地 Operator Console 的 {page} 页面处理。"
        "请运行 `uv run cobo-wallet-operator` 后再操作。"
    )
    return {
        "request": request,
        "decision": "forbidden",
        "allowed": False,
        "category": category,
        "matched_rules": matched_rules,
        "reply_policy": "直接返回 refusal_message，不要尝试调用其他钱包工具绕过。",
        "refusal_message": refusal_message,
        "operator_console_command": "uv run cobo-wallet-operator",
        "operator_console_page": page,
    }


def handle(context: ToolContext, request: str) -> dict:
    raw = request.strip()
    normalized = raw.lower()

    if not raw:
        raise ValueError("request 不能为空")

    query_verbs = [
        "看",
        "查看",
        "查询",
        "显示",
        "列出",
        "多少",
        "状态",
        "list",
        "show",
        "query",
        "check",
    ]
    modify_verbs = [
        "加入",
        "加进",
        "放进",
        "新增",
        "添加",
        "增加",
        "改",
        "改名",
        "修改",
        "更新",
        "删除",
        "移除",
        "撤销",
        "切换",
        "关闭",
        "开启",
        "设置",
        "设成",
        "调成",
        "变成",
        "充值",
        "存入",
        "入金",
        "出金",
        "提取",
        "withdraw",
        "deposit",
        "set ",
        "update",
        "delete",
        "remove",
        "add ",
        "allow",
        "authorize",
        "authorise",
        "permit",
        "rename",
        "rotate",
        "switch",
        "enable",
        "disable",
        "change",
        "top up",
    ]
    toggle_verbs = ["开启", "关闭", "enable", "disable", "turn on", "turn off"]
    has_query_verb = _contains_any(raw, query_verbs) or _contains_any(normalized, query_verbs)
    has_modify_verb = _contains_any(raw, modify_verbs) or _contains_any(normalized, modify_verbs)
    has_amount_hint = (
        bool(re.search(r"\b\d+(\.\d+)?\s*(eth|usdt|btc)\b", normalized))
        or _contains_any(raw, ["金额"])
    )

    address_book_keywords_raw = ["地址簿", "联系人", "收款人", "常用收款人", "别名"]
    address_book_keywords_normalized = ["recipient", "address book", "recipient book", "alias"]
    whitelist_keywords_raw = ["白名单", "允许名单"]
    whitelist_keywords_normalized = ["whitelist", "allowlist", "allow list"]
    balance_keywords_raw = ["余额", "充值", "入金", "出金", "提取"]
    balance_keywords_normalized = ["balance", "fund", "funding", "deposit", "withdraw", "top up"]
    policy_keywords_raw = [
        "限额",
        "权限",
        "策略",
        "管理员 pin",
        "管理员PIN",
        "PIN",
        "本地授权",
        "执行模式",
        "写入权限",
        "只读模式",
        "白名单开关",
        "白名单策略",
    ]
    policy_keywords_normalized = [
        "policy",
        "limit",
        "pin",
        "permission",
        "execution mode",
        "local auth",
        "write enabled",
        "write_enabled",
        "demo_write_enabled",
        "demo_require_local_auth",
        "demo_require_whitelist",
        "readonly",
        "read only",
        "sepolia",
        "simulate",
    ]
    has_address_book_keyword = _contains_any(raw, address_book_keywords_raw) or _contains_any(
        normalized, address_book_keywords_normalized
    )
    has_whitelist_keyword = _contains_any(raw, whitelist_keywords_raw) or _contains_any(
        normalized, whitelist_keywords_normalized
    )
    has_balance_keyword = _contains_any(raw, balance_keywords_raw) or _contains_any(
        normalized, balance_keywords_normalized
    )
    has_policy_keyword = _contains_any(raw, policy_keywords_raw) or _contains_any(
        normalized, policy_keywords_normalized
    )
    has_address_book_write_intent = (
        has_address_book_keyword and has_modify_verb
    ) or _contains_any(raw, ["重命名", "设为我的常用收款人"]) or _contains_any(
        normalized,
        ["rename recipient", "set as recipient", "favorite recipient"],
    )
    has_whitelist_write_intent = (
        has_whitelist_keyword and has_modify_verb
    ) or (
        _contains_any(raw, ["允许", "放行", "授权"])
        and _contains_any(raw, ["转账"])
        and not has_amount_hint
    ) or _contains_any(normalized, ["authorize recipient", "allow recipient", "permit recipient"])
    has_balance_write_intent = has_balance_keyword and (
        has_modify_verb
        or _contains_any(raw, ["模拟入金", "人工出金"])
        or _contains_any(normalized, ["top up"])
    ) or _matches_balance_adjustment_intent(raw, normalized)
    has_policy_write_intent = has_policy_keyword and (
        has_modify_verb
        or _contains_any(raw, ["切换"])
        or _contains_any(normalized, toggle_verbs)
    )

    if _contains_any(raw, ["私钥"]) or _contains_any(normalized, ["private key", "demo_private_key"]):
        result = _operator_only_response(
            request=raw,
            category="wallet_config_management",
            area="私钥配置",
            page="Wallet",
            matched_rules=["private_key_management"],
        )
    elif _contains_any(raw, ["rpc"]) or _contains_any(normalized, ["rpc", "sepolia_rpc_url"]):
        result = _operator_only_response(
            request=raw,
            category="wallet_config_management",
            area="RPC 配置",
            page="Wallet",
            matched_rules=["rpc_management"],
        )
    elif has_address_book_write_intent:
        result = _operator_only_response(
            request=raw,
            category="address_book_management",
            area="地址簿修改",
            page="Address Book",
            matched_rules=["address_book_write"],
        )
    elif has_whitelist_keyword and (
        _contains_any(raw, ["开启", "关闭"]) or _contains_any(normalized, toggle_verbs)
    ):
        result = _operator_only_response(
            request=raw,
            category="policy_management",
            area="白名单策略开关修改",
            page="Policy",
            matched_rules=["whitelist_policy_write"],
        )
    elif has_whitelist_write_intent:
        result = _operator_only_response(
            request=raw,
            category="whitelist_management",
            area="白名单修改",
            page="Whitelist",
            matched_rules=["whitelist_write"],
        )
    elif has_balance_write_intent:
        result = _operator_only_response(
            request=raw,
            category="balance_management",
            area="模拟余额调整",
            page="Balance Lab",
            matched_rules=["balance_write"],
        )
    elif has_policy_write_intent:
        result = _operator_only_response(
            request=raw,
            category="policy_management",
            area="策略与权限开关修改",
            page="Policy",
            matched_rules=["policy_write"],
        )
    elif _contains_any(raw, ["收款信息", "收款地址", "收款名片"]) or _contains_any(
        normalized,
        ["receive", "receive card", "deposit address"],
    ):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "receive_card_query",
            "matched_rules": ["receive_card_read"],
            "suggested_tool": "wallet_get_receive_card",
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif has_address_book_keyword and has_query_verb:
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "recipient_query",
            "matched_rules": ["address_book_read"],
            "suggested_tool": "wallet_list_recipients",
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif has_whitelist_keyword:
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "whitelist_query",
            "matched_rules": ["whitelist_read"],
            "suggested_tool": "wallet_list_whitelist",
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif proposal_id := _match_proposal_id(raw):
        if _contains_any(raw, ["取消"]) or _contains_any(normalized, ["cancel"]):
            suggested_tool = "wallet_cancel_proposal"
            category = "proposal_cancel"
        elif _contains_any(raw, ["确认"]) or _contains_any(normalized, ["confirm"]):
            suggested_tool = "wallet_confirm_proposal"
            category = "proposal_confirm"
        else:
            suggested_tool = "wallet_get_proposal"
            category = "proposal_query"
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": category,
            "matched_rules": ["proposal_explicit_id"],
            "suggested_tool": suggested_tool,
            "suggested_parameters": {"proposal_id": proposal_id},
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif tx_hash := _match_tx_hash(raw):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "transaction_status_query",
            "matched_rules": ["tx_hash_explicit"],
            "suggested_tool": "wallet_get_transaction_status",
            "suggested_parameters": {"tx_hash": tx_hash},
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif _contains_any(raw, ["交易历史", "最近交易", "最近10条交易", "最近 10 条交易"]) or _contains_any(
        normalized,
        ["transaction history", "transactions"],
    ):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "transaction_history_query",
            "matched_rules": ["transaction_history_read"],
            "suggested_tool": "wallet_list_transactions",
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    elif _contains_any(raw, ["提案", "proposal"]) or _contains_any(normalized, ["proposal"]):
        if _contains_any(raw, ["取消"]) or _contains_any(normalized, ["cancel"]):
            suggested_tool = "wallet_cancel_proposal"
            category = "proposal_cancel_contextual"
        elif _contains_any(raw, ["确认"]) or _contains_any(normalized, ["confirm"]):
            suggested_tool = "wallet_confirm_proposal"
            category = "proposal_confirm_contextual"
        else:
            suggested_tool = "wallet_list_proposals"
            category = "proposal_list_query"
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": category,
            "matched_rules": ["proposal_contextual"],
            "suggested_tool": suggested_tool,
            "reply_policy": "可以继续调用 suggested_tool；如果缺少 proposal_id，应先向用户确认具体是哪一笔。",
        }
    elif _contains_any(raw, ["确认"]) or _contains_any(normalized, ["confirm"]):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "proposal_confirm_contextual",
            "matched_rules": ["confirm_contextual"],
            "suggested_tool": "wallet_confirm_proposal",
            "reply_policy": "如果上下文里没有明确 proposal_id，应先向用户确认具体是哪一笔。",
        }
    elif _contains_any(raw, ["取消"]) or _contains_any(normalized, ["cancel"]):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "proposal_cancel_contextual",
            "matched_rules": ["cancel_contextual"],
            "suggested_tool": "wallet_cancel_proposal",
            "reply_policy": "如果上下文里没有明确 proposal_id，应先向用户确认具体是哪一笔。",
        }
    elif _contains_any(raw, ["转", "转账"]) or _contains_any(normalized, ["send", "transfer", "pay"]):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "transfer_prepare",
            "matched_rules": ["transfer_flow"],
            "suggested_tool": "wallet_prepare_transfer",
            "reply_policy": (
                "可以继续调用 suggested_tool；如果缺少金额或收款对象，应先向用户确认。"
                "如果后续执行阶段被运行时策略拦截，例如 DEMO_WRITE_ENABLED=false，"
                "应明确说明这是运行时开关问题，而不是 Agent 权限不足。"
            ),
        }
    elif _contains_any(raw, ["钱包状态", "总览", "余额"]) or _contains_any(
        normalized,
        ["overview", "wallet status", "balance"],
    ):
        result = {
            "request": raw,
            "decision": "allowed",
            "allowed": True,
            "category": "wallet_overview_query",
            "matched_rules": ["wallet_overview_read"],
            "suggested_tool": "wallet_get_overview",
            "reply_policy": "可以继续调用 suggested_tool。",
        }
    else:
        result = {
            "request": raw,
            "decision": "unclear",
            "allowed": False,
            "category": "unknown",
            "matched_rules": [],
            "reply_policy": "先不要调用其他钱包工具。应先澄清用户是想查询、转账，还是在请求人工后台权限。",
            "clarification_message": (
                "我还不能准确判断这个请求属于钱包查询、转账流程，还是人工后台管理动作。"
                "请再明确一点，例如：查看总览、查看联系人、显示收款信息、发起转账、确认提案、取消提案。"
            ),
        }

    context.audit_store.append(
        "wallet_check_request_capability",
        {
            "request": raw,
            "decision": result["decision"],
            "category": result["category"],
        },
    )
    return result
