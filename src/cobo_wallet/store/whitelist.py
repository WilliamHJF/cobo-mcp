from __future__ import annotations

from pathlib import Path

from web3 import Web3

from cobo_wallet.config.env import Settings
from cobo_wallet.models import WhitelistEntry
from cobo_wallet.store.common import read_json, write_json


class WhitelistStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.demo_data_dir) / "whitelist.json"

    def list(self) -> list[WhitelistEntry]:
        raw = read_json(self.path, default=None)
        if raw is None:
            self.save([])
            raw = []
        return [WhitelistEntry.model_validate(item) for item in raw]

    def save(self, entries: list[dict]) -> None:
        write_json(self.path, entries)

    def save_entries(self, entries: list[WhitelistEntry]) -> None:
        self.save([entry.model_dump(mode="json", exclude_none=True) for entry in entries])

    def is_allowed(self, address: str) -> bool:
        return self.get_by_address(address) is not None

    def get_by_address(self, address: str) -> WhitelistEntry | None:
        checksum_address = self._normalize_address(address)
        for entry in self.list():
            if entry.address == checksum_address:
                return entry
        return None

    def allow_entry(
        self,
        *,
        address: str,
        name: str | None = None,
        note: str | None = None,
    ) -> tuple[WhitelistEntry, bool]:
        entries = self.list()
        normalized_address = self._normalize_address(address)
        normalized_name = self._normalize_name(name)
        normalized_note = self._normalize_note(note)

        existing_index = self._find_index_by_address(entries, normalized_address)
        if existing_index is not None:
            current = entries[existing_index]
            updated = current.model_copy(
                update={
                    "name": normalized_name if normalized_name is not None else current.name,
                    "note": normalized_note if normalized_note is not None else current.note,
                }
            )
            self._assert_unique_name(entries, updated, skip_index=existing_index)
            entries[existing_index] = updated
            self.save_entries(entries)
            return updated, False

        entry = WhitelistEntry(
            address=normalized_address,
            name=normalized_name,
            note=normalized_note,
        )
        self._assert_unique_name(entries, entry)
        entries.append(entry)
        self.save_entries(entries)
        return entry, True

    def revoke_entry(self, identifier: str) -> WhitelistEntry:
        entries = self.list()
        index = self._find_index_by_identifier(entries, identifier)
        if index is None:
            raise ValueError(f"未找到白名单地址: {identifier}")
        entry = entries.pop(index)
        self.save_entries(entries)
        return entry

    def _find_index_by_address(
        self,
        entries: list[WhitelistEntry],
        address: str,
    ) -> int | None:
        for index, entry in enumerate(entries):
            if entry.address == address:
                return index
        return None

    def _find_index_by_identifier(
        self,
        entries: list[WhitelistEntry],
        identifier: str,
    ) -> int | None:
        candidate = identifier.strip()
        if not candidate:
            raise ValueError("白名单名称或地址不能为空")

        if Web3.is_address(candidate):
            checksum_address = self._normalize_address(candidate)
            return self._find_index_by_address(entries, checksum_address)

        lowered = candidate.lower()
        for index, entry in enumerate(entries):
            if entry.name and entry.name.lower() == lowered:
                return index
        return None

    def _normalize_address(self, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("白名单地址不能为空")
        if not Web3.is_address(candidate):
            raise ValueError(f"白名单地址格式不正确: {value}")
        return Web3.to_checksum_address(candidate)

    def _normalize_name(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_note(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _assert_unique_name(
        self,
        entries: list[WhitelistEntry],
        candidate: WhitelistEntry,
        *,
        skip_index: int | None = None,
    ) -> None:
        if candidate.name is None:
            return
        lowered_name = candidate.name.lower()
        for index, entry in enumerate(entries):
            if skip_index is not None and index == skip_index:
                continue
            if entry.name and entry.name.lower() == lowered_name:
                raise ValueError(f"白名单名称重复: {candidate.name}")
