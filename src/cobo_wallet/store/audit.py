from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from cobo_wallet.config.env import Settings
from cobo_wallet.store.common import ensure_parent


class AuditStore:
    def __init__(self, settings: Settings) -> None:
        self.path = Path(settings.demo_data_dir) / "audit.jsonl"

    def append(self, action: str, payload: dict) -> None:
        ensure_parent(self.path)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
