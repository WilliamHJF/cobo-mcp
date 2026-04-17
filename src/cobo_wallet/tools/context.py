from __future__ import annotations

from dataclasses import dataclass

from cobo_wallet.config.env import Settings
from cobo_wallet.policy.engine import PolicyEngine
from cobo_wallet.store.address_book import AddressBookStore
from cobo_wallet.store.audit import AuditStore
from cobo_wallet.store.proposals import ProposalStore
from cobo_wallet.wallet.service import WalletService


@dataclass(slots=True)
class ToolContext:
    settings: Settings
    policy_engine: PolicyEngine
    address_book_store: AddressBookStore
    proposal_store: ProposalStore
    audit_store: AuditStore
    wallet_service: WalletService
