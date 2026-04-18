from __future__ import annotations

import argparse
import json
import sys

from cobo_wallet.server import build_context
from cobo_wallet.policy.engine import PolicyError
from cobo_wallet.tools import (
    add_recipient,
    allow_recipient,
    cancel_proposal,
    confirm_proposal,
    confirm_transfer,
    create_transfer_proposal,
    delete_recipient,
    estimate_transfer,
    get_account,
    get_balance,
    get_proposal,
    get_receive_card,
    get_transaction_status,
    list_whitelist,
    list_proposals,
    list_recipients,
    list_policy,
    list_transactions,
    request_local_authorization,
    revoke_recipient,
    update_recipient,
)


def _print(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="COBO Wallet MCP 本地演示 CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("account", help="查看当前钱包账户信息")
    subparsers.add_parser("balance", help="查看当前钱包余额")
    subparsers.add_parser("policy", help="查看当前策略配置")
    subparsers.add_parser("recipients", help="查看本地地址簿联系人")
    subparsers.add_parser("receive-card", help="查看适合展示或转发的收款信息")
    subparsers.add_parser("list-whitelist", help="查看当前白名单地址")
    list_proposals_parser = subparsers.add_parser(
        "list-proposals", help="查看本地提案列表，默认优先显示未完成提案"
    )
    list_proposals_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最多返回多少条提案，默认 20",
    )
    list_proposals_parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help=(
            "按提案状态过滤，可重复传多次。"
            "例如 pending / confirmed_by_user / awaiting_local_authorization /"
            " authorized / executed / expired / rejected"
        ),
    )
    list_transactions_parser = subparsers.add_parser(
        "list-transactions", help="查看最近转账历史，包含已执行和已取消提案"
    )
    list_transactions_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最多返回多少条历史记录，默认 20",
    )

    add_recipient_parser = subparsers.add_parser("add-recipient", help="新增地址簿联系人")
    add_recipient_parser.add_argument("--name", required=True, help="联系人名称")
    add_recipient_parser.add_argument("--address", required=True, help="联系人地址")
    add_recipient_parser.add_argument(
        "--alias",
        action="append",
        dest="aliases",
        help="联系人别名，可重复传多次",
    )
    add_recipient_parser.add_argument("--note", help="联系人备注")

    allow_recipient_parser = subparsers.add_parser(
        "allow-recipient", help="将联系人或地址加入白名单"
    )
    allow_recipient_parser.add_argument(
        "--target",
        required=True,
        help="联系人名称、别名或完整地址",
    )
    allow_recipient_parser.add_argument(
        "--name",
        help="白名单展示名称，可选；不传时默认只保存地址",
    )
    allow_recipient_parser.add_argument("--note", help="白名单备注，可选")

    revoke_recipient_parser = subparsers.add_parser(
        "revoke-recipient", help="将联系人或地址从白名单中移除"
    )
    revoke_recipient_parser.add_argument(
        "--target",
        required=True,
        help="白名单名称或完整地址",
    )

    update_recipient_parser = subparsers.add_parser(
        "update-recipient", help="更新地址簿联系人"
    )
    update_recipient_parser.add_argument(
        "--name-or-alias",
        required=True,
        help="现有联系人名称或别名，用于定位联系人",
    )
    update_recipient_parser.add_argument("--name", help="新的联系人名称")
    update_recipient_parser.add_argument("--address", help="新的联系人地址")
    update_recipient_parser.add_argument(
        "--alias",
        action="append",
        dest="aliases",
        help="新的别名列表，可重复传多次；传入后会覆盖旧别名",
    )
    update_recipient_parser.add_argument(
        "--note",
        help="新的联系人备注；传入后会覆盖旧备注",
    )

    delete_recipient_parser = subparsers.add_parser(
        "delete-recipient", help="删除地址簿联系人"
    )
    delete_recipient_parser.add_argument(
        "--name-or-alias",
        required=True,
        help="现有联系人名称或别名",
    )

    estimate_parser = subparsers.add_parser("estimate", help="预估一笔转账的成本")
    estimate_parser.add_argument("--to", required=True, help="收款地址或联系人名称")
    estimate_parser.add_argument("--amount", required=True, help="转账金额，单位 ETH")

    propose_parser = subparsers.add_parser("propose", help="创建一条待审批的转账提案")
    propose_parser.add_argument("--to", required=True, help="收款地址或联系人名称")
    propose_parser.add_argument("--amount", required=True, help="转账金额，单位 ETH")

    get_proposal_parser = subparsers.add_parser(
        "get-proposal", help="查看一条提案的详细状态"
    )
    get_proposal_parser.add_argument("--proposal-id", required=True, help="提案编号")

    cancel_proposal_parser = subparsers.add_parser(
        "cancel-proposal", help="取消一条尚未执行的提案"
    )
    cancel_proposal_parser.add_argument("--proposal-id", required=True, help="提案编号")

    confirm_proposal_parser = subparsers.add_parser(
        "confirm-proposal", help="记录用户已经在对话里确认这条提案"
    )
    confirm_proposal_parser.add_argument("--proposal-id", required=True, help="待确认提案编号")

    request_auth_parser = subparsers.add_parser(
        "request-auth", help="将提案推进到等待本地授权状态"
    )
    request_auth_parser.add_argument("--proposal-id", required=True, help="待授权提案编号")

    authorize_parser = subparsers.add_parser(
        "authorize", help="在本地终端输入 PIN，完成一次性授权"
    )
    authorize_parser.add_argument("--proposal-id", required=True, help="待授权提案编号")
    authorize_parser.add_argument("--pin", help="本地 PIN，仅建议用于自动化测试")

    confirm_parser = subparsers.add_parser("confirm", help="执行一条已经本地审批的提案")
    confirm_parser.add_argument("--proposal-id", required=True, help="待执行提案编号")

    tx_parser = subparsers.add_parser("tx-status", help="查看交易状态")
    tx_parser.add_argument("--tx-hash", required=True, help="交易哈希")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    context = build_context()

    try:
        if args.command == "account":
            _print(get_account.handle(context))
            return

        if args.command == "balance":
            _print(get_balance.handle(context))
            return

        if args.command == "policy":
            _print(list_policy.handle(context))
            return

        if args.command == "recipients":
            _print(list_recipients.handle(context))
            return

        if args.command == "receive-card":
            _print(get_receive_card.handle(context))
            return

        if args.command == "list-whitelist":
            _print(list_whitelist.handle(context))
            return

        if args.command == "list-transactions":
            _print(list_transactions.handle(context, limit=args.limit))
            return

        if args.command == "allow-recipient":
            result = allow_recipient.handle(
                context,
                target=args.target,
                name=args.name,
                note=args.note,
            )
            _print(result)
            return

        if args.command == "revoke-recipient":
            result = revoke_recipient.handle(
                context,
                target=args.target,
            )
            _print(result)
            return

        if args.command == "add-recipient":
            result = add_recipient.handle(
                context,
                name=args.name,
                address=args.address,
                aliases=args.aliases,
                note=args.note,
            )
            _print(result)
            return

        if args.command == "update-recipient":
            result = update_recipient.handle(
                context,
                name_or_alias=args.name_or_alias,
                name=args.name,
                address=args.address,
                aliases=args.aliases,
                note=args.note,
            )
            _print(result)
            return

        if args.command == "delete-recipient":
            result = delete_recipient.handle(
                context,
                name_or_alias=args.name_or_alias,
            )
            _print(result)
            return

        if args.command == "list-proposals":
            _print(
                list_proposals.handle(
                    context,
                    limit=args.limit,
                    statuses=args.statuses,
                )
            )
            return

        if args.command == "estimate":
            result = estimate_transfer.handle(
                context,
                to=args.to,
                amount=args.amount,
            )
            _print(result)
            return

        if args.command == "propose":
            result = create_transfer_proposal.handle(
                context,
                to=args.to,
                amount=args.amount,
            )
            _print(result)
            return

        if args.command == "get-proposal":
            result = get_proposal.handle(context, proposal_id=args.proposal_id)
            _print(result)
            return

        if args.command == "cancel-proposal":
            result = cancel_proposal.handle(context, proposal_id=args.proposal_id)
            _print(result)
            return

        if args.command == "confirm-proposal":
            result = confirm_proposal.handle(context, proposal_id=args.proposal_id)
            _print(result)
            return

        if args.command == "request-auth":
            result = request_local_authorization.handle(
                context, proposal_id=args.proposal_id
            )
            _print(result)
            return

        if args.command == "authorize":
            from scripts.approve_proposal import main as approve_main

            sys.argv = [
                "approve_proposal.py",
                "--proposal-id",
                args.proposal_id,
            ]
            if args.pin:
                sys.argv.extend(["--pin", args.pin])
            approve_main()
            return

        if args.command == "confirm":
            result = confirm_transfer.handle(context, proposal_id=args.proposal_id)
            _print(result)
            return

        if args.command == "tx-status":
            result = get_transaction_status.handle(context, tx_hash=args.tx_hash)
            _print(result)
            return
    except (PolicyError, RuntimeError, ValueError) as exc:
        _print({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
