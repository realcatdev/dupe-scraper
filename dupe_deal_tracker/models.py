from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class Listing:
    id: str
    hash_name: str
    item_name: str
    price: float
    category: str
    asset_id: Optional[str]
    floatvalue: Optional[float]
    instant_fulfill: bool

    @classmethod
    def from_api(cls, raw: Mapping[str, Any]) -> "Listing":
        hash_name = str(raw.get("hash_name") or raw.get("item_name") or "")
        return cls(
            id=str(raw.get("id") or ""),
            hash_name=hash_name,
            item_name=str(raw.get("item_name") or hash_name),
            price=float(raw.get("price") or 0),
            category=str(raw.get("category") or ""),
            asset_id=str(raw["asset_id"]) if raw.get("asset_id") is not None else None,
            floatvalue=_optional_float(raw.get("floatvalue")),
            instant_fulfill=bool(raw.get("instant_fulfill")),
        )


@dataclass(frozen=True)
class Deal:
    listing: Listing
    typical_price: float
    discount_percent: float
    expected_profit: float
    source: str


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
