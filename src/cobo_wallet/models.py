from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


ProposalStatus = Literal[
    "pending",
    "confirmed_by_user",
    "awaiting_local_authorization",
    "authorized",
    "executed",
    "expired",
    "rejected",
]


class Proposal(BaseModel):
    proposal_id: str
    requested_to: str | None = None
    recipient_name: str | None = None
    to: str
    amount_eth: str
    amount_wei: str
    chain_id: int
    intent_hash: str
    status: ProposalStatus = "pending"
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_confirmed_at: datetime | None = None
    local_authorized_at: datetime | None = None
    authorization_expires_at: datetime | None = None
    authorization_token: str | None = None
    tx_hash: str | None = None
    executed_at: datetime | None = None
    canceled_at: datetime | None = None
    estimated_fee_eth: str | None = None
    balance_before_eth: str | None = None


class ToolResult(BaseModel):
    ok: bool = True
    message: str
    data: dict = Field(default_factory=dict)


class RecipientEntry(BaseModel):
    name: str
    address: str
    aliases: list[str] = Field(default_factory=list)
    note: str | None = None


class WhitelistEntry(BaseModel):
    address: str
    name: str | None = None
    note: str | None = None


class WalletState(BaseModel):
    address: str
    network: str = "Ethereum Sepolia"
    chain_id: int
    execution_mode: str
    configured: bool
    write_enabled: bool
    simulated_balance_eth: str


class PolicySnapshot(BaseModel):
    chain_id: int
    write_enabled: bool
    execution_mode: str
    max_transfer_eth: str
    proposal_ttl_minutes: int
    local_authorization_ttl_minutes: int
    local_authorization_required: bool = True
    whitelist_required: bool = False
    asset: str = "ETH"
    network: str = "Ethereum Sepolia"
