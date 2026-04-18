from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from cobo_wallet.operator.service import OperatorConsoleService, OperatorError


PAGE_TITLE = "COBO Operator Console"
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")
FLASH_KEY = "operator_console_flash"


def main() -> None:
    from streamlit.web.cli import main as st_main
    import sys

    sys.argv = ["streamlit", "run", str(Path(__file__).resolve())]
    raise SystemExit(st_main())


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(199, 170, 118, 0.10), transparent 28%),
                radial-gradient(circle at top right, rgba(22, 50, 74, 0.08), transparent 24%),
                var(--background-color);
            color: var(--text-color);
        }
        .block-container {
            max-width: 1320px;
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
        }
        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(22, 50, 74, 0.18) 0%, rgba(22, 50, 74, 0.06) 100%),
                var(--secondary-background-color);
            border-right: 1px solid rgba(127, 127, 127, 0.18);
        }
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stCaptionContainer,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div {
            color: var(--text-color);
        }
        div[data-testid="stMetric"] {
            background: rgba(127, 127, 127, 0.08);
            border: 1px solid rgba(127, 127, 127, 0.18);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            box-shadow: 0 10px 24px rgba(26, 38, 48, 0.06);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(127, 127, 127, 0.18);
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(26, 38, 48, 0.05);
        }
        .console-hero {
            padding: 1.2rem 1.3rem;
            border: 1px solid rgba(127, 127, 127, 0.18);
            border-radius: 24px;
            background:
                radial-gradient(circle at right top, rgba(199, 170, 118, 0.16), transparent 28%),
                linear-gradient(135deg, rgba(127, 127, 127, 0.08), rgba(127, 127, 127, 0.04));
            box-shadow: 0 18px 36px rgba(26, 38, 48, 0.08);
            margin-bottom: 1rem;
        }
        .console-kicker {
            font-size: 0.76rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--primary-color) !important;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }
        .console-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-color) !important;
            margin: 0 0 0.35rem 0;
        }
        .console-subtitle {
            font-size: 0.98rem;
            color: var(--text-color) !important;
            opacity: 0.78;
            margin: 0;
            line-height: 1.6;
        }
        .console-card {
            border: 1px solid rgba(127, 127, 127, 0.18);
            border-radius: 18px;
            background: rgba(127, 127, 127, 0.08);
            padding: 1rem 1.05rem;
            min-height: 112px;
            box-shadow: 0 10px 26px rgba(26, 38, 48, 0.05);
        }
        .console-card-label {
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-color) !important;
            opacity: 0.68;
            margin-bottom: 0.55rem;
            font-weight: 700;
        }
        .console-card-value {
            font-size: 1.12rem;
            line-height: 1.35;
            color: var(--text-color) !important;
            font-weight: 700;
            word-break: break-word;
        }
        .console-card-help {
            margin-top: 0.55rem;
            font-size: 0.82rem;
            color: var(--text-color) !important;
            opacity: 0.72;
            line-height: 1.45;
        }
        .console-pill {
            display: inline-block;
            margin: 0 0.35rem 0.35rem 0;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .console-pill-neutral {
            background: rgba(127, 127, 127, 0.12);
            color: var(--text-color) !important;
            border-color: rgba(127, 127, 127, 0.18);
        }
        .console-pill-ok {
            background: rgba(53, 170, 106, 0.16);
            color: #1f7a49 !important;
            border-color: rgba(53, 170, 106, 0.22);
        }
        .console-pill-warn {
            background: rgba(223, 154, 52, 0.16);
            color: #a86200 !important;
            border-color: rgba(223, 154, 52, 0.24);
        }
        .console-pill-danger {
            background: rgba(214, 83, 83, 0.16);
            color: #b13a3a !important;
            border-color: rgba(214, 83, 83, 0.24);
        }
        .console-section-note {
            color: var(--text-color) !important;
            opacity: 0.78;
            font-size: 0.92rem;
            line-height: 1.6;
        }
        .stApp code {
            color: var(--text-color) !important;
            background: rgba(127, 127, 127, 0.10) !important;
            border: 1px solid rgba(127, 127, 127, 0.16);
            border-radius: 0.4rem;
            padding: 0.12rem 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _push_flash(level: str, message: str, *, details: dict[str, Any] | None = None) -> None:
    st.session_state[FLASH_KEY] = {
        "level": level,
        "message": message,
        "details": details or {},
    }


def _show_flash() -> None:
    payload = st.session_state.pop(FLASH_KEY, None)
    if not payload:
        return
    level = payload["level"]
    message = payload["message"]
    details = payload.get("details") or {}
    render = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }.get(level, st.info)
    render(message)
    if details:
        _show_detail_list("本次操作结果", details)


def _render_page_header(title: str, description: str, *, kicker: str = "Operator Console") -> None:
    st.markdown(
        f"""
        <div class="console-hero">
            <div class="console-kicker">{escape(kicker)}</div>
            <div class="console-title">{escape(title)}</div>
            <p class="console-subtitle">{escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(cards: list[tuple[str, str, str | None]]) -> None:
    if not cards:
        return
    columns = st.columns(len(cards))
    for column, (label, value, help_text) in zip(columns, cards):
        with column:
            help_html = (
                f'<div class="console-card-help">{escape(help_text)}</div>'
                if help_text
                else ""
            )
            st.markdown(
                f"""
                <div class="console-card">
                    <div class="console-card-label">{escape(label)}</div>
                    <div class="console-card-value">{escape(value)}</div>
                    {help_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_pills(items: list[tuple[str, str]]) -> None:
    if not items:
        return
    html = []
    for text, tone in items:
        safe_tone = tone if tone in {"neutral", "ok", "warn", "danger"} else "neutral"
        html.append(
            f'<span class="console-pill console-pill-{safe_tone}">{escape(text)}</span>'
        )
    st.markdown("".join(html), unsafe_allow_html=True)


def _show_detail_list(title: str, values: dict[str, Any], *, columns: int = 2) -> None:
    entries = [(key, _stringify(value)) for key, value in values.items()]
    if not entries:
        return

    with st.container(border=True):
        st.markdown(f"**{title}**")
        for index in range(0, len(entries), columns):
            cols = st.columns(columns)
            for column, entry in zip(cols, entries[index : index + columns]):
                label, value = entry
                column.caption(label)
                column.markdown(f"`{value}`")


def _show_dataframe(rows: list[dict[str, Any]], *, height: int = 360) -> None:
    if not rows:
        st.info("当前没有可展示的数据。")
        return
    dataframe = pd.DataFrame(rows)
    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        height=min(height, 96 + max(len(dataframe), 1) * 36),
    )


def _parse_aliases(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _stringify(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, list):
        return "、".join(_stringify(item) for item in value) or "-"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _format_amount(value: Any) -> str:
    if value in (None, "", "-"):
        return "-"
    return f"{value} ETH"


def _format_timestamp(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        candidate = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            candidate = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    if candidate.tzinfo is None:
        candidate = candidate.replace(tzinfo=LOCAL_TIMEZONE)
    return candidate.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def _format_execution_mode(mode: Any) -> str:
    mapping = {
        "simulate": "本地模拟",
        "sepolia": "Sepolia",
        None: "-",
    }
    return mapping.get(mode, str(mode))


def _format_balance_source(source: Any) -> str:
    mapping = {
        "wallet_state": "本地状态文件",
        "chain_rpc": "链上 RPC",
        None: "-",
    }
    return mapping.get(source, str(source))


def _format_event_type(value: Any) -> str:
    mapping = {
        "deposit": "模拟入金",
        "withdraw": "模拟出金",
        "set_balance": "直接设定余额",
    }
    return mapping.get(value, str(value))


def _format_flag(value: bool, *, on: str = "已开启", off: str = "已关闭") -> str:
    return on if value else off


def _format_actions(actions: list[str] | None) -> str:
    if not actions:
        return "-"
    mapping = {
        "wallet_confirm_proposal": "确认提案",
        "wallet_cancel_proposal": "取消提案",
        "wallet_execute_transfer": "执行转账",
        "wallet_get_transaction_status": "查看状态",
        "local_authorization": "本地授权",
    }
    return "、".join(mapping.get(action, action) for action in actions)


def _short_address(value: Any, *, head: int = 8, tail: int = 6) -> str:
    if not value:
        return "-"
    text = str(value)
    if len(text) <= head + tail + 3:
        return text
    return f"{text[:head]}...{text[-tail:]}"


def _proposal_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "状态": item.get("status_display") or item.get("status"),
                "收款对象": item.get("recipient_name") or item.get("requested_to") or "-",
                "金额": _format_amount(item.get("amount_eth")),
                "总成本": _format_amount(item.get("estimated_total_cost_eth")),
                "下一步": _format_actions(item.get("next_allowed_actions")),
                "时间": _format_timestamp(item.get("happened_at") or item.get("created_at")),
            }
        )
    return rows


def _transaction_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "时间": _format_timestamp(item.get("happened_at")),
                "类型": "已执行" if item.get("record_type") == "executed" else "已取消",
                "收款对象": item.get("recipient_name") or item.get("requested_to") or "-",
                "金额": _format_amount(item.get("amount_eth")),
                "手续费": _format_amount(item.get("estimated_fee_eth")),
                "总成本": _format_amount(item.get("estimated_total_cost_eth")),
            }
        )
    return rows


def _funding_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        target = item.get("source_label") or item.get("target_label") or "-"
        rows.append(
            {
                "时间": _format_timestamp(item.get("timestamp")),
                "类型": _format_event_type(item.get("event_type")),
                "金额": _format_amount(item.get("amount_eth")),
                "变更后余额": _format_amount(item.get("balance_after_eth")),
                "来源 / 去向": target,
                "备注": item.get("note") or "-",
            }
        )
    return rows


def _whitelist_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "名称": item.get("name") or item.get("recipient_name") or "-",
            "地址": item.get("address"),
            "备注": item.get("note") or item.get("recipient_note") or "-",
        }
        for item in items
    ]


def _recipient_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "名称": item.get("name"),
            "地址": item.get("address"),
            "别名": "、".join(item.get("aliases", [])) or "-",
            "备注": item.get("note") or "-",
        }
        for item in items
    ]


def _login(service: OperatorConsoleService) -> None:
    _render_page_header(
        "管理员登录",
        "这个控制台只开放给人工管理员，用于处理私钥、白名单、地址簿、模拟余额和策略开关等敏感配置。",
        kicker="Local Access Only",
    )
    center = st.columns([1, 1.15, 1])[1]
    with center:
        with st.container(border=True):
            st.markdown("**输入管理员 PIN 进入控制台**")
            st.caption("这里的所有修改都直接作用于本地项目配置，不通过 MCP。")
            with st.form("operator-login"):
                pin = st.text_input("管理员 PIN", type="password")
                submitted = st.form_submit_button("进入控制台", use_container_width=True)
                if submitted:
                    try:
                        service.verify_operator_pin(pin)
                    except OperatorError as exc:
                        st.error(str(exc))
                        return
                    st.session_state["operator_authenticated"] = True
                    st.rerun()


def _dashboard_page(service: OperatorConsoleService) -> None:
    dashboard = service.get_dashboard()
    overview = dashboard["overview"]
    account = overview["account"]
    balance = overview["balance"]
    runtime_policy = overview["policy"]
    operator_policy = service.get_policy_config()
    state_management = overview["state_management"]

    _render_page_header(
        "总览",
        "集中查看钱包身份、权限状态、最近转账提案和人工资金调整。适合作为人工后台的第一屏。",
    )
    _render_pills(
        [
            (f"执行模式: {_format_execution_mode(account['execution_mode'])}", "warn" if account["execution_mode"] == "simulate" else "neutral"),
            (f"写入权限: {_format_flag(account['write_enabled'])}", "ok" if account["write_enabled"] else "danger"),
            (f"白名单: {_format_flag(operator_policy['require_whitelist'])}", "ok" if operator_policy["require_whitelist"] else "neutral"),
            (f"本地授权: {_format_flag(operator_policy['require_local_auth'])}", "ok" if operator_policy["require_local_auth"] else "neutral"),
        ]
    )
    _render_summary_cards(
        [
            ("当前余额", _format_amount(balance["balance_eth"]), "控制台展示已统一为钱包风格小数位"),
            ("单笔限额", _format_amount(operator_policy["max_transfer_eth"]), "超过这个金额的转账提案会被拒绝"),
            ("收款名单", f"{overview['recipient_count']} 个联系人 / {overview['whitelist_count']} 条白名单", None),
        ]
    )

    detail_left, detail_right = st.columns(2)
    with detail_left:
        _show_detail_list(
            "钱包信息",
            {
                "钱包地址": account["address"],
                "网络": account["network"],
                "Chain ID": account["chain_id"],
                "余额来源": _format_balance_source(state_management["balance_source"]),
            },
        )
    with detail_right:
        _show_detail_list(
            "控制开关",
            {
                "允许写入": _format_flag(runtime_policy["write_enabled"]),
                "白名单模式": _format_flag(operator_policy["require_whitelist"]),
                "本地授权": _format_flag(operator_policy["require_local_auth"]),
                "提案有效期": f"{operator_policy['proposal_ttl_minutes']} 分钟",
                "授权有效期": f"{operator_policy['local_auth_ttl_minutes']} 分钟",
                "数据目录": service.settings.demo_data_dir,
            },
        )

    proposal_tab, transaction_tab, funding_tab = st.tabs(
        ["最近提案", "最近交易 / 取消", "最近人工资金调整"]
    )
    with proposal_tab:
        _show_dataframe(_proposal_rows(dashboard["recent_proposals"].get("proposals", [])))
    with transaction_tab:
        _show_dataframe(
            _transaction_rows(dashboard["recent_transactions"].get("transactions", []))
        )
    with funding_tab:
        _show_dataframe(_funding_rows(dashboard["recent_funding_events"]))


def _wallet_page(service: OperatorConsoleService) -> None:
    config = service.get_wallet_config()
    account = service.context.wallet_service.get_account_summary()

    _render_page_header(
        "钱包配置",
        "这里只处理 RPC 和私钥配置。页面不会回显私钥全文，只展示是否已配置以及派生地址。",
    )
    _render_summary_cards(
        [
            ("网络", config["network"], None),
            ("Chain ID", str(config["chain_id"]), None),
            ("私钥状态", "已配置" if config["private_key_configured"] else "未配置", "私钥只能在人工后台修改"),
        ]
    )

    left, right = st.columns([1.15, 0.85])
    with left:
        with st.container(border=True):
            st.markdown("**更新 RPC / 私钥**")
            st.caption("保存后会立即刷新本地运行时配置。")
            with st.form("wallet-config-form"):
                rpc_url = st.text_input("Sepolia RPC URL", value=config["sepolia_rpc_url"])
                private_key = st.text_input("新的私钥（留空表示不修改）", type="password")
                submitted = st.form_submit_button("保存钱包配置", use_container_width=True)
                if submitted:
                    try:
                        updated = service.update_wallet_config(
                            sepolia_rpc_url=rpc_url,
                            private_key=private_key,
                            clear_private_key=False,
                        )
                    except OperatorError as exc:
                        st.error(str(exc))
                    else:
                        _push_flash(
                            "success",
                            "钱包配置已更新。",
                            details={
                                "派生地址": updated["derived_address"],
                                "网络": updated["network"],
                                "Chain ID": updated["chain_id"],
                                "私钥状态": "已配置" if updated["private_key_configured"] else "未配置",
                            },
                        )
                        st.rerun()

    with right:
        with st.container(border=True):
            st.markdown("**安全提示**")
            st.markdown(
                """
                <div class="console-section-note">
                1. 私钥不会在界面中回显。<br/>
                2. 模拟模式下，这里的地址仍然可以作为真实链上收款地址展示。<br/>
                3. 是否允许 Agent 发起或执行转账，取决于 Policy 页面里的写入和策略开关。
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("清除当前私钥", type="secondary", use_container_width=True):
                updated = service.update_wallet_config(
                    sepolia_rpc_url=config["sepolia_rpc_url"],
                    private_key=None,
                    clear_private_key=True,
                )
                _push_flash(
                    "warning",
                    "当前私钥已清除。",
                    details={
                        "派生地址": updated["derived_address"],
                        "私钥状态": "未配置",
                    },
                )
                st.rerun()

    _show_detail_list(
        "当前配置明细",
        {
            "派生地址": config["derived_address"],
            "网络": config["network"],
            "Chain ID": config["chain_id"],
            "RPC 已配置": "是" if bool(config["sepolia_rpc_url"]) else "否",
            "私钥已配置": "是" if config["private_key_configured"] else "否",
            "执行模式": _format_execution_mode(account["execution_mode"]),
        },
    )


def _balance_page(service: OperatorConsoleService) -> None:
    balance = service.context.wallet_service.get_balance()

    _render_page_header(
        "模拟资金实验室",
        "这里只影响本地模拟余额，不会向真实链广播任何资金变动。适合测试提案、扣款和历史流水。",
    )
    _render_summary_cards(
        [
            ("当前模拟余额", _format_amount(balance["balance_eth"]), None),
            ("余额来源", _format_balance_source(balance["balance_source"]), None),
            ("状态文件", _short_address(balance.get("wallet_state_path"), head=22, tail=16), balance.get("wallet_state_path") or "-"),
        ]
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("**模拟入金**")
            st.caption("用于测试“从外部账户转入本钱包”的效果。")
            with st.form("deposit-form"):
                deposit_amount = st.text_input("模拟入金金额 (ETH)", value="1")
                deposit_source = st.text_input("资金来源说明", value="外部测试账户")
                deposit_note = st.text_input("备注", value="人工模拟入金")
                submitted = st.form_submit_button("执行入金", use_container_width=True)
                if submitted:
                    try:
                        event = service.deposit_balance(
                            amount_eth=deposit_amount,
                            source_label=deposit_source,
                            note=deposit_note,
                        )
                    except OperatorError as exc:
                        st.error(str(exc))
                    else:
                        _push_flash("success", "模拟入金已记录。", details=event)
                        st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("**模拟出金**")
            st.caption("用于测试“从本钱包转出到外部账户”的效果。")
            with st.form("withdraw-form"):
                withdraw_amount = st.text_input("模拟出金金额 (ETH)", value="0.5")
                withdraw_target = st.text_input("去向说明", value="外部测试账户")
                withdraw_note = st.text_input("备注", value="人工模拟出金")
                submitted = st.form_submit_button("执行出金", use_container_width=True)
                if submitted:
                    try:
                        event = service.withdraw_balance(
                            amount_eth=withdraw_amount,
                            target_label=withdraw_target,
                            note=withdraw_note,
                        )
                    except OperatorError as exc:
                        st.error(str(exc))
                    else:
                        _push_flash("success", "模拟出金已记录。", details=event)
                        st.rerun()

    with col3:
        with st.container(border=True):
            st.markdown("**直接设定余额**")
            st.caption("适合快速把测试环境调到某个起始余额。")
            with st.form("set-balance-form"):
                target_balance = st.text_input(
                    "直接设定余额 (ETH)",
                    value=balance["balance_eth"],
                )
                set_note = st.text_input("备注", value="人工调整测试余额")
                submitted = st.form_submit_button("设置余额", use_container_width=True)
                if submitted:
                    try:
                        event = service.set_balance(
                            target_balance_eth=target_balance,
                            note=set_note,
                        )
                    except OperatorError as exc:
                        st.error(str(exc))
                    else:
                        _push_flash("success", "模拟余额已更新。", details=event)
                        st.rerun()

    st.markdown("**最近资金调整记录**")
    _show_dataframe(_funding_rows(service.list_funding_events(limit=20)), height=440)


def _whitelist_page(service: OperatorConsoleService) -> None:
    entries = service.context.whitelist_store.list()
    entry_rows: list[dict[str, Any]] = []
    for entry in entries:
        item = entry.model_dump(mode="json", exclude_none=True)
        recipient = service.context.address_book_store.get_by_address(entry.address)
        if recipient is not None:
            item["recipient_name"] = recipient.name
            if recipient.note:
                item["recipient_note"] = recipient.note
        if "name" not in item and recipient is not None:
            item["name"] = recipient.name
        if "note" not in item and recipient is not None and recipient.note:
            item["note"] = recipient.note
        entry_rows.append(item)
    policy = service.get_policy_config()

    _render_page_header(
        "白名单管理",
        "这里维护允许转账的收款地址集合。即使白名单列表存在，只有在 Policy 页面开启白名单模式后才会真正生效。",
    )
    _render_summary_cards(
        [
            ("白名单条目", str(len(entry_rows)), None),
            ("白名单开关", _format_flag(policy["require_whitelist"]), None),
            ("执行模式", _format_execution_mode(policy["execution_mode"]), None),
        ]
    )

    left, right = st.columns([1.25, 0.75])
    with left:
        st.markdown("**当前白名单**")
        _show_dataframe(_whitelist_rows(entry_rows), height=440)

    with right:
        with st.container(border=True):
            st.markdown("**新增或更新条目**")
            st.caption("`target` 可以填写地址，也可以填写地址簿中的联系人名称或别名。")
            with st.form("whitelist-add-form"):
                target = st.text_input("target")
                name = st.text_input("展示名（可选）")
                note = st.text_input("备注（可选）")
                submitted = st.form_submit_button("加入白名单", use_container_width=True)
                if submitted:
                    try:
                        result = service.add_whitelist_entry(target=target, name=name, note=note)
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                    else:
                        _push_flash("success", result["message"], details=result["entry"])
                        st.rerun()

        with st.container(border=True):
            st.markdown("**移除条目**")
            if entry_rows:
                options = [
                    (row["address"], f"{row.get('name') or '未命名'} | {_short_address(row['address'])}")
                    for row in entry_rows
                ]
                selected_address = st.selectbox(
                    "选择要移除的条目",
                    options=[item[0] for item in options],
                    format_func=lambda value: next(
                        label for address, label in options if address == value
                    ),
                    key="whitelist-remove-select",
                )
                if st.button("移除白名单项", type="secondary", use_container_width=True):
                    try:
                        result = service.revoke_whitelist_entry(selected_address)
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                    else:
                        _push_flash("warning", result["message"])
                        st.rerun()
            else:
                st.info("当前还没有白名单条目。")


def _address_book_page(service: OperatorConsoleService) -> None:
    recipients = service.context.address_book_store.list()
    recipient_rows = [entry.model_dump(mode="json") for entry in recipients]
    alias_count = sum(len(item.get("aliases", [])) for item in recipient_rows)

    _render_page_header(
        "地址簿管理",
        "这里维护人名、别名和地址之间的映射。Agent 能读这些联系人，但不能自己修改。",
    )
    _render_summary_cards(
        [
            ("联系人数量", str(len(recipient_rows)), None),
            ("别名总数", str(alias_count), None),
            ("默认示例", "burn", "项目初始化时会自动写入 burn 销毁地址"),
        ]
    )

    left, right = st.columns([1.2, 0.8])
    with left:
        st.markdown("**当前地址簿**")
        _show_dataframe(_recipient_rows(recipient_rows), height=480)

    with right:
        add_tab, edit_tab, delete_tab = st.tabs(["新增", "编辑", "删除"])

        with add_tab:
            with st.container(border=True):
                with st.form("recipient-add-form"):
                    add_name = st.text_input("名称")
                    add_address = st.text_input("地址")
                    add_aliases = st.text_input("别名（英文逗号分隔）")
                    add_note = st.text_input("备注")
                    submitted = st.form_submit_button("新增联系人", use_container_width=True)
                    if submitted:
                        try:
                            result = service.add_address_book_entry(
                                name=add_name,
                                address=add_address,
                                aliases=_parse_aliases(add_aliases),
                                note=add_note,
                            )
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                        else:
                            _push_flash("success", result["message"], details=result["recipient"])
                            st.rerun()

        with edit_tab:
            with st.container(border=True):
                if recipient_rows:
                    selected_name = st.selectbox(
                        "选择联系人",
                        options=[row["name"] for row in recipient_rows],
                        key="recipient-edit-select",
                    )
                    selected = next(row for row in recipient_rows if row["name"] == selected_name)
                    with st.form("recipient-edit-form"):
                        edit_name = st.text_input("名称", value=selected["name"])
                        edit_address = st.text_input("地址", value=selected["address"])
                        edit_aliases = st.text_input(
                            "别名（英文逗号分隔）",
                            value=", ".join(selected.get("aliases", [])),
                        )
                        edit_note = st.text_input("备注", value=selected.get("note") or "")
                        submitted = st.form_submit_button("保存修改", use_container_width=True)
                        if submitted:
                            try:
                                result = service.update_address_book_entry(
                                    name_or_alias=selected_name,
                                    name=edit_name,
                                    address=edit_address,
                                    aliases=_parse_aliases(edit_aliases),
                                    note=edit_note,
                                )
                            except Exception as exc:  # noqa: BLE001
                                st.error(str(exc))
                            else:
                                _push_flash("success", result["message"], details=result["recipient"])
                                st.rerun()
                else:
                    st.info("当前地址簿为空。")

        with delete_tab:
            with st.container(border=True):
                if recipient_rows:
                    selected_name = st.selectbox(
                        "选择要删除的联系人",
                        options=[row["name"] for row in recipient_rows],
                        key="recipient-delete-select",
                    )
                    selected = next(row for row in recipient_rows if row["name"] == selected_name)
                    st.caption(f"将删除联系人 `{selected['name']}`，地址 `{_short_address(selected['address'])}`。")
                    if st.button("删除当前联系人", type="secondary", use_container_width=True):
                        try:
                            result = service.delete_address_book_entry(selected_name)
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                        else:
                            _push_flash("warning", result["message"])
                            st.rerun()
                else:
                    st.info("当前地址簿为空。")


def _policy_page(service: OperatorConsoleService) -> None:
    policy = service.get_policy_config()

    _render_page_header(
        "策略设置",
        "这些配置属于人工后台专属。它们会影响 Agent 能否继续执行转账流程，但 Agent 本身不能修改这些开关。",
    )
    _render_summary_cards(
        [
            ("写入权限", _format_flag(policy["write_enabled"]), None),
            ("执行模式", _format_execution_mode(policy["execution_mode"]), None),
            ("白名单模式", _format_flag(policy["require_whitelist"]), None),
            ("本地授权", _format_flag(policy["require_local_auth"]), None),
        ]
    )
    _show_detail_list(
        "当前策略参数",
        {
            "单笔最大转账": _format_amount(policy["max_transfer_eth"]),
            "提案有效期": f"{policy['proposal_ttl_minutes']} 分钟",
            "本地授权有效期": f"{policy['local_auth_ttl_minutes']} 分钟",
            "管理员 PIN 已配置": "是" if policy["operator_pin_configured"] else "否",
        },
    )

    with st.container(border=True):
        st.markdown("**编辑策略**")
        st.caption("保存后立即生效。MCP 常驻进程会在每次调用前重新加载这些配置。")
        with st.form("policy-form"):
            top_left, top_right = st.columns(2)
            with top_left:
                write_enabled = st.checkbox("允许写入", value=policy["write_enabled"])
                require_whitelist = st.checkbox("启用白名单", value=policy["require_whitelist"])
                max_transfer_eth = st.text_input("单笔最大转账 ETH", value=policy["max_transfer_eth"])
            with top_right:
                execution_mode = st.selectbox(
                    "执行模式",
                    options=["simulate", "sepolia"],
                    index=0 if policy["execution_mode"] == "simulate" else 1,
                )
                require_local_auth = st.checkbox(
                    "启用本地授权", value=policy["require_local_auth"]
                )
                operator_pin = st.text_input("新的管理员 PIN（留空表示不修改）", type="password")

            bottom_left, bottom_right = st.columns(2)
            with bottom_left:
                proposal_ttl_minutes = st.number_input(
                    "提案有效期（分钟）",
                    min_value=1,
                    value=int(policy["proposal_ttl_minutes"]),
                    step=1,
                )
            with bottom_right:
                local_auth_ttl_minutes = st.number_input(
                    "本地授权有效期（分钟）",
                    min_value=1,
                    value=int(policy["local_auth_ttl_minutes"]),
                    step=1,
                )

            submitted = st.form_submit_button("保存策略", use_container_width=True)
            if submitted:
                try:
                    updated = service.update_policy_config(
                        write_enabled=write_enabled,
                        execution_mode=execution_mode,
                        require_whitelist=require_whitelist,
                        require_local_auth=require_local_auth,
                        max_transfer_eth=max_transfer_eth,
                        proposal_ttl_minutes=int(proposal_ttl_minutes),
                        local_auth_ttl_minutes=int(local_auth_ttl_minutes),
                        operator_pin=operator_pin,
                    )
                except OperatorError as exc:
                    st.error(str(exc))
                else:
                    _push_flash(
                        "success",
                        "策略已更新。",
                        details={
                            "写入权限": _format_flag(updated["write_enabled"]),
                            "执行模式": _format_execution_mode(updated["execution_mode"]),
                            "白名单模式": _format_flag(updated["require_whitelist"]),
                            "本地授权": _format_flag(updated["require_local_auth"]),
                            "单笔限额": _format_amount(updated["max_transfer_eth"]),
                        },
                    )
                    st.rerun()


def run_app() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon="C",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()
    service = OperatorConsoleService()

    if not st.session_state.get("operator_authenticated", False):
        _login(service)
        return

    with st.sidebar:
        st.markdown(f"### {PAGE_TITLE}")
        st.caption("本地人工后台，不通过 MCP。")
        st.markdown("---")
        st.caption(f"数据目录: `{service.settings.demo_data_dir}`")
        st.caption(
            "钱包状态文件: "
            f"`{service.context.wallet_service.get_balance_source_info()['wallet_state_path'] or '-'}`"
        )
        _render_pills(
            [
                (
                    f"写入 {_format_flag(service.settings.demo_write_enabled, on='开启', off='关闭')}",
                    "ok" if service.settings.demo_write_enabled else "danger",
                ),
                (
                    _format_execution_mode(service.settings.demo_execution_mode),
                    "warn" if service.settings.demo_execution_mode == "simulate" else "neutral",
                ),
            ]
        )

        page = st.radio(
            "页面",
            ["总览", "钱包配置", "模拟资金", "白名单", "地址簿", "策略"],
        )
        if st.button("退出登录", use_container_width=True):
            st.session_state["operator_authenticated"] = False
            st.rerun()

    _show_flash()

    if page == "总览":
        _dashboard_page(service)
    elif page == "钱包配置":
        _wallet_page(service)
    elif page == "模拟资金":
        _balance_page(service)
    elif page == "白名单":
        _whitelist_page(service)
    elif page == "地址簿":
        _address_book_page(service)
    elif page == "策略":
        _policy_page(service)


if __name__ == "__main__":
    run_app()
