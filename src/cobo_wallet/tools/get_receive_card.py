from __future__ import annotations

from cobo_wallet.tools.context import ToolContext


def _build_explorer_address_url(*, chain_id: int, address: str) -> str | None:
    if not address or address == "UNCONFIGURED":
        return None
    if chain_id == 11155111:
        return f"https://sepolia.etherscan.io/address/{address}"
    return None


def _build_share_text(*, network: str, asset: str, address: str, warning: str) -> str:
    return "\n".join(
        [
            "收款信息",
            f"网络: {network}",
            f"资产: {asset}",
            f"地址: {address}",
            f"提示: {warning}",
        ]
    )


def _build_display_markdown(
    *,
    network: str,
    asset: str,
    address: str,
    explorer_address_url: str | None,
    warning: str,
    operator_note: str | None,
) -> str:
    lines = [
        "这是当前钱包的收款信息：",
        "",
        f"- 网络：`{network}`",
        f"- 资产：`{asset}`",
        f"- 地址：`{address}`",
    ]
    if explorer_address_url:
        lines.append(f"- 浏览器：`{explorer_address_url}`")
    lines.append(f"- 提示：{warning}")
    if operator_note:
        lines.extend(
            [
                "",
                f"补充说明：{operator_note}",
            ]
        )
    return "\n".join(lines)


def handle(context: ToolContext) -> dict:
    account = context.wallet_service.get_account_summary()
    address = account["address"]
    wallet_fully_configured = account["configured"]
    address_ready = address != "UNCONFIGURED"
    network = account["network"]
    chain_id = account["chain_id"]
    execution_mode = account["execution_mode"]
    asset = "ETH"
    title = "我的收款信息"

    if not address_ready:
        result = {
            "title": title,
            "configured": False,
            "wallet_fully_configured": wallet_fully_configured,
            "share_ready": False,
            "address": address,
            "network": network,
            "chain_id": chain_id,
            "asset": asset,
            "message": "当前钱包尚未配置私钥，无法生成有效收款信息。",
            "display_markdown": (
                "当前钱包尚未配置私钥，无法生成有效收款信息。"
                "请先在 `.env` 中完成钱包配置后再使用该工具。"
            ),
        }
        context.audit_store.append("wallet_get_receive_card", {"configured": False})
        return result

    warning = f"请仅向该地址转入 {network} 上的 {asset}，不要转入其他网络或不兼容资产。"
    explorer_address_url = _build_explorer_address_url(
        chain_id=chain_id,
        address=address,
    )
    operator_note = None
    if not wallet_fully_configured:
        operator_note = (
            "当前钱包还没有完整配置 RPC 或发送能力。"
            "这不会影响别人向该地址转账，但会影响本地读取链上余额或真实广播交易。"
        )
    elif execution_mode == "simulate":
        operator_note = (
            "当前项目处于 simulate 模式。"
            "这张收款信息可用于展示真实链上地址，但系统不会自动把真实链上入账同步到本地模拟余额。"
        )
    share_text = _build_share_text(
        network=network,
        asset=asset,
        address=address,
        warning=warning,
    )
    result = {
        "title": title,
        "configured": True,
        "wallet_fully_configured": wallet_fully_configured,
        "share_ready": True,
        "address": address,
        "network": network,
        "chain_id": chain_id,
        "asset": asset,
        "execution_mode": execution_mode,
        "warning": warning,
        "operator_note": operator_note,
        "explorer_address_url": explorer_address_url,
        "share_text": share_text,
        "display_markdown": _build_display_markdown(
            network=network,
            asset=asset,
            address=address,
            explorer_address_url=explorer_address_url,
            warning=warning,
            operator_note=operator_note,
        ),
        "assistant_usage_hint": (
            "当用户想看收款信息时，请优先展示 display_markdown；"
            "当用户想把收款信息转发给别人时，请优先使用 share_text。"
        ),
        "natural_language_examples": [
            "显示我的收款信息",
            "把我的收款地址发给我",
            "生成一段可以转发给别人的收款文本",
            "别人怎么给我的钱包转账",
            "生成我的收款名片",
        ],
        "message": "返回适合 Codex 展示和转发的收款信息。",
    }
    context.audit_store.append(
        "wallet_get_receive_card",
        {"configured": True, "address": address, "network": network},
    )
    return result
