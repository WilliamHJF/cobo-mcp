from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from cobo_wallet.amounts import format_eth_display, format_eth_storage
from cobo_wallet.config.env import Settings
from cobo_wallet.store.common import ensure_parent


class FundingEventStore:
    def __init__(self, settings: Settings) -> None:
        self.path = Path(settings.demo_data_dir) / "funding_events.jsonl"

    def append(self, payload: dict) -> dict:
        ensure_parent(self.path)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
        self._normalize_numeric_fields(record, formatter=format_eth_storage)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def list(self, limit: int = 50) -> list[dict]:
        if not self.path.exists():
            return []

        records: list[dict] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._normalize_numeric_fields(record, formatter=format_eth_display)
                records.append(record)
        records.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
        return records[:limit]

    def _normalize_numeric_fields(self, item: dict, *, formatter) -> None:
        for field in ("amount_eth", "balance_before_eth", "balance_after_eth"):
            value = item.get(field)
            if value is None:
                continue
            item[field] = formatter(value)
