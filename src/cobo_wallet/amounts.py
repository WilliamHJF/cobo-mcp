from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


ETH_STORAGE_DECIMALS = 18
ETH_DISPLAY_DECIMALS = 8

_ETH_STORAGE_QUANT = Decimal("1e-18")
_ETH_DISPLAY_QUANT = Decimal("1e-8")


def to_decimal(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_eth_storage(value: Decimal | str | int | float) -> str:
    normalized = to_decimal(value).quantize(_ETH_STORAGE_QUANT, rounding=ROUND_DOWN)
    return _format_decimal(normalized)


def format_eth_display(value: Decimal | str | int | float) -> str:
    normalized = to_decimal(value).quantize(_ETH_DISPLAY_QUANT, rounding=ROUND_HALF_UP)
    return _format_decimal(normalized)


def format_optional_eth_storage(value: Decimal | str | int | float | None) -> str | None:
    if value is None:
        return None
    return format_eth_storage(value)


def format_optional_eth_display(value: Decimal | str | int | float | None) -> str | None:
    if value is None:
        return None
    return format_eth_display(value)
