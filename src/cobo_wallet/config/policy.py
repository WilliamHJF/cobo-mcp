from __future__ import annotations

from cobo_wallet.config.env import Settings
from cobo_wallet.models import PolicySnapshot


def build_policy_snapshot(settings: Settings) -> PolicySnapshot:
    return PolicySnapshot(
        chain_id=settings.demo_chain_id,
        write_enabled=settings.demo_write_enabled,
        execution_mode=settings.demo_execution_mode,
        max_transfer_eth=settings.demo_max_transfer_eth,
        proposal_ttl_minutes=settings.demo_proposal_ttl_minutes,
        local_authorization_required=settings.demo_require_local_authorization,
        whitelist_required=settings.demo_require_whitelist,
        local_authorization_ttl_minutes=settings.demo_local_authorization_ttl_minutes,
    )
