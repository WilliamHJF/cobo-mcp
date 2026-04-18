from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    app_name: str = "COBO Wallet MCP"
    sepolia_rpc_url: str = Field(default="")
    demo_private_key: str = Field(default="")
    demo_write_enabled: bool = Field(default=False)
    demo_execution_mode: str = Field(default="simulate")
    demo_simulated_balance_eth: str = Field(default="50")
    demo_require_local_authorization: bool = Field(default=False)
    demo_require_whitelist: bool = Field(default=False)
    demo_approval_pin: str = Field(default="246810")
    demo_chain_id: int = Field(default=11155111)
    demo_max_transfer_eth: str = Field(default="0.05")
    demo_proposal_ttl_minutes: int = Field(default=30)
    demo_local_authorization_ttl_minutes: int = Field(default=5)
    demo_data_dir: Path = Field(default=ROOT_DIR / "data")

    @property
    def is_wallet_configured(self) -> bool:
        return bool(self.sepolia_rpc_url and self.demo_private_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        sepolia_rpc_url=os.getenv("SEPOLIA_RPC_URL", ""),
        demo_private_key=os.getenv("DEMO_PRIVATE_KEY", ""),
        demo_write_enabled=_as_bool(os.getenv("DEMO_WRITE_ENABLED"), default=False),
        demo_execution_mode=os.getenv("DEMO_EXECUTION_MODE", "simulate").strip().lower(),
        demo_simulated_balance_eth=os.getenv("DEMO_SIMULATED_BALANCE_ETH", "50"),
        demo_require_local_authorization=_as_bool(
            os.getenv("DEMO_REQUIRE_LOCAL_AUTH"), default=False
        ),
        demo_require_whitelist=_as_bool(
            os.getenv("DEMO_REQUIRE_WHITELIST"), default=False
        ),
        demo_approval_pin=os.getenv("DEMO_APPROVAL_PIN", "246810"),
        demo_chain_id=int(os.getenv("DEMO_CHAIN_ID", "11155111")),
        demo_max_transfer_eth=os.getenv("DEMO_MAX_TRANSFER_ETH", "0.05"),
        demo_proposal_ttl_minutes=int(os.getenv("DEMO_PROPOSAL_TTL_MINUTES", "30")),
        demo_local_authorization_ttl_minutes=int(
            os.getenv("DEMO_LOCAL_AUTH_TTL_MINUTES", "5")
        ),
        demo_data_dir=Path(os.getenv("DEMO_DATA_DIR", str(ROOT_DIR / "data"))),
    )
