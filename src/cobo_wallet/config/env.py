from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT_ENV_VAR = "COBO_PROJECT_ROOT"
ENV_FILE_ENV_VAR = "COBO_ENV_FILE"
PROJECT_ROOT_MARKERS = ("pyproject.toml", ".git")


def _resolve_path(value: str | Path, *, base_dir: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve(strict=False)


def _find_ancestor_with_markers(start: Path, markers: tuple[str, ...]) -> Path | None:
    current = start.resolve(strict=False)
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return None


def _discover_project_root() -> Path:
    override = os.getenv(PROJECT_ROOT_ENV_VAR)
    if override:
        return _resolve_path(override, base_dir=Path.cwd())

    for start in (Path.cwd(), Path(__file__).resolve(strict=False)):
        resolved = _find_ancestor_with_markers(start, PROJECT_ROOT_MARKERS)
        if resolved is not None:
            return resolved

    return Path.cwd().resolve(strict=False)


def _discover_env_path(root_dir: Path) -> Path:
    override = os.getenv(ENV_FILE_ENV_VAR)
    if override:
        return _resolve_path(override, base_dir=Path.cwd())

    for start in (Path.cwd(), Path(__file__).resolve(strict=False)):
        resolved = _find_ancestor_with_markers(start, (".env",))
        if resolved is not None:
            return (resolved / ".env").resolve(strict=False)

    return (root_dir / ".env").resolve(strict=False)


def _default_data_dir(*, root_dir: Path, env_path: Path) -> Path:
    base_dir = env_path.parent if env_path.name == ".env" else root_dir
    return (base_dir / "data").resolve(strict=False)


def _resolve_data_dir(raw_value: str | None, *, root_dir: Path, env_path: Path) -> Path:
    if raw_value is None or not raw_value.strip():
        return _default_data_dir(root_dir=root_dir, env_path=env_path)
    return _resolve_path(raw_value.strip(), base_dir=env_path.parent)


ROOT_DIR = _discover_project_root()
ENV_PATH = _discover_env_path(ROOT_DIR)
load_dotenv(ENV_PATH)


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    app_name: str = "COBO Wallet MCP"
    sepolia_rpc_url: str = Field(default="")
    demo_private_key: str = Field(default="")
    demo_operator_pin: str = Field(default="")
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
        demo_operator_pin=os.getenv(
            "DEMO_OPERATOR_PIN",
            os.getenv("DEMO_APPROVAL_PIN", ""),
        ),
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
        demo_data_dir=_resolve_data_dir(
            os.getenv("DEMO_DATA_DIR"),
            root_dir=ROOT_DIR,
            env_path=ENV_PATH,
        ),
    )


def reload_env_file() -> Settings:
    load_dotenv(ENV_PATH, override=True)
    get_settings.cache_clear()
    return get_settings()
