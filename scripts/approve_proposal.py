from __future__ import annotations

import argparse
import getpass
import secrets
from datetime import UTC, datetime, timedelta

from cobo_wallet.config.env import get_settings
from cobo_wallet.store.audit import AuditStore
from cobo_wallet.store.proposals import ProposalStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authorize a transfer proposal locally with PIN.")
    parser.add_argument("--proposal-id", required=True, help="待审批提案编号")
    parser.add_argument("--pin", help="本地 PIN。仅建议用于自动化测试，不建议手动明文输入。")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    proposal_store = ProposalStore(settings)
    audit_store = AuditStore(settings)

    if not settings.demo_require_local_authorization:
        raise SystemExit("当前配置已关闭本地 PIN 授权，不需要运行这个命令")

    proposal = proposal_store.get(args.proposal_id)
    if proposal is None:
        raise SystemExit(f"提案不存在: {args.proposal_id}")
    if proposal.status != "awaiting_local_authorization":
        raise SystemExit(
            f"提案当前状态为 {proposal.status}，只有 awaiting_local_authorization 状态才能进行本地授权"
        )

    pin = args.pin or getpass.getpass("请输入本地授权 PIN: ")
    if pin != settings.demo_approval_pin:
        audit_store.append(
            "local_authorization_failed",
            {"proposal_id": args.proposal_id, "reason": "invalid_pin"},
        )
        raise SystemExit("PIN 错误，授权失败")

    authorized_at = datetime.now(UTC)
    authorization_expires_at = authorized_at + timedelta(
        minutes=settings.demo_local_authorization_ttl_minutes
    )
    proposal_store.mark_local_authorized(
        args.proposal_id,
        user_confirmed_at=proposal.user_confirmed_at,
        local_authorized_at=authorized_at,
        authorization_expires_at=authorization_expires_at,
        authorization_token=secrets.token_hex(16),
    )
    audit_store.append("local_authorize_proposal", {"proposal_id": args.proposal_id})
    print(
        "已完成本地授权: "
        f"{args.proposal_id}，授权窗口将在 {authorization_expires_at.isoformat()} 失效"
    )


if __name__ == "__main__":
    main()
