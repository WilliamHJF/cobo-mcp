from __future__ import annotations

from pathlib import Path

from web3 import Web3

from cobo_wallet.config.env import Settings
from cobo_wallet.models import RecipientEntry
from cobo_wallet.store.common import read_json, write_json


DEFAULT_RECIPIENTS = [
    {
        "name": "burn",
        "address": "0x000000000000000000000000000000000000dEaD",
        "aliases": ["dead", "销毁地址", "黑洞地址"],
        "note": "测试常用的销毁地址",
    }
]


class AddressBookStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.demo_data_dir) / "address_book.json"

    def list(self) -> list[RecipientEntry]:
        raw = read_json(self.path, default=None)
        if raw is None:
            self.save(DEFAULT_RECIPIENTS)
            raw = DEFAULT_RECIPIENTS
        return [RecipientEntry.model_validate(item) for item in raw]

    def save(self, entries: list[dict]) -> None:
        write_json(self.path, entries)

    def save_entries(self, entries: list[RecipientEntry]) -> None:
        self.save([entry.model_dump(mode="json") for entry in entries])

    def add_entry(
        self,
        *,
        name: str,
        address: str,
        aliases: list[str] | None = None,
        note: str | None = None,
    ) -> RecipientEntry:
        entries = self.list()
        candidate = self._build_entry(
            name=name,
            address=address,
            aliases=aliases,
            note=note,
        )
        self._assert_unique_identifiers(entries, candidate)
        entries.append(candidate)
        self.save_entries(entries)
        return candidate

    def update_entry(
        self,
        identifier: str,
        *,
        name: str | None = None,
        address: str | None = None,
        aliases: list[str] | None = None,
        note: str | None = None,
    ) -> tuple[RecipientEntry, RecipientEntry]:
        entries = self.list()
        match = self._find_entry(entries, identifier)
        if match is None:
            raise ValueError(f"未找到联系人: {identifier}")

        index, current = match
        if name is None and address is None and aliases is None and note is None:
            raise ValueError("至少要提供一个要更新的字段")

        updated = self._build_entry(
            name=name if name is not None else current.name,
            address=address if address is not None else current.address,
            aliases=aliases if aliases is not None else current.aliases,
            note=note if note is not None else current.note,
        )
        self._assert_unique_identifiers(entries, updated, skip_index=index)
        entries[index] = updated
        self.save_entries(entries)
        return current, updated

    def delete_entry(self, identifier: str) -> RecipientEntry:
        entries = self.list()
        match = self._find_entry(entries, identifier)
        if match is None:
            raise ValueError(f"未找到联系人: {identifier}")

        index, current = match
        entries.pop(index)
        self.save_entries(entries)
        return current

    def resolve(self, value: str) -> dict:
        candidate = value.strip()
        if not candidate:
            raise ValueError("收款地址或联系人名称不能为空")

        if Web3.is_address(candidate):
            checksum_address = Web3.to_checksum_address(candidate)
            return {
                "requested_to": value,
                "resolved_to": checksum_address,
                "recipient_name": None,
                "matched_by": "address",
            }

        lowered = candidate.lower()
        for entry in self.list():
            if entry.name.lower() == lowered:
                return {
                    "requested_to": value,
                    "resolved_to": Web3.to_checksum_address(entry.address),
                    "recipient_name": entry.name,
                    "matched_by": "name",
                }
            for alias in entry.aliases:
                if alias.lower() == lowered:
                    return {
                        "requested_to": value,
                        "resolved_to": Web3.to_checksum_address(entry.address),
                        "recipient_name": entry.name,
                        "matched_by": "alias",
                    }

        known = [entry.name for entry in self.list()]
        suggestion = "、".join(known[:10]) if known else "当前地址簿为空"
        raise ValueError(
            f"未找到收款对象: {value}。你可以传完整地址，或使用已配置联系人名称，例如：{suggestion}"
        )

    def _find_entry(
        self, entries: list[RecipientEntry], identifier: str
    ) -> tuple[int, RecipientEntry] | None:
        candidate = identifier.strip().lower()
        if not candidate:
            raise ValueError("联系人名称或别名不能为空")

        for index, entry in enumerate(entries):
            if entry.name.lower() == candidate:
                return index, entry
            for alias in entry.aliases:
                if alias.lower() == candidate:
                    return index, entry
        return None

    def _build_entry(
        self,
        *,
        name: str,
        address: str,
        aliases: list[str] | None,
        note: str | None,
    ) -> RecipientEntry:
        normalized_name = self._normalize_name(name)
        normalized_address = self._normalize_address(address)
        normalized_aliases = self._normalize_aliases(
            aliases=aliases,
            reserved_name=normalized_name,
        )
        normalized_note = self._normalize_note(note)
        return RecipientEntry(
            name=normalized_name,
            address=normalized_address,
            aliases=normalized_aliases,
            note=normalized_note,
        )

    def _normalize_name(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("联系人名称不能为空")
        return normalized

    def _normalize_address(self, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("联系人地址不能为空")
        if not Web3.is_address(candidate):
            raise ValueError(f"联系人地址格式不正确: {value}")
        return Web3.to_checksum_address(candidate)

    def _normalize_aliases(
        self,
        *,
        aliases: list[str] | None,
        reserved_name: str,
    ) -> list[str]:
        if aliases is None:
            return []

        normalized: list[str] = []
        seen: set[str] = {reserved_name.lower()}
        for alias in aliases:
            item = alias.strip()
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            normalized.append(item)
            seen.add(lowered)
        return normalized

    def _normalize_note(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _assert_unique_identifiers(
        self,
        entries: list[RecipientEntry],
        candidate: RecipientEntry,
        *,
        skip_index: int | None = None,
    ) -> None:
        existing: dict[str, tuple[str, str]] = {}
        for index, entry in enumerate(entries):
            if skip_index is not None and index == skip_index:
                continue
            existing[entry.name.lower()] = ("name", entry.name)
            for alias in entry.aliases:
                existing[alias.lower()] = ("alias", entry.name)

        self._ensure_identifier_available(
            candidate.name,
            identifier_type="名称",
            existing=existing,
        )
        for alias in candidate.aliases:
            self._ensure_identifier_available(
                alias,
                identifier_type="别名",
                existing=existing,
            )

    def _ensure_identifier_available(
        self,
        identifier: str,
        *,
        identifier_type: str,
        existing: dict[str, tuple[str, str]],
    ) -> None:
        conflict = existing.get(identifier.lower())
        if conflict is None:
            return
        conflict_kind, owner_name = conflict
        if conflict_kind == "name":
            raise ValueError(
                f"{identifier_type} {identifier} 与现有联系人名称 {owner_name} 冲突"
            )
        raise ValueError(
            f"{identifier_type} {identifier} 与联系人 {owner_name} 的别名冲突"
        )
