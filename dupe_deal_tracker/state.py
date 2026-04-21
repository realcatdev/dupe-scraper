from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PricePoint:
    typical_price: float
    samples: int
    updated_at: str


class PriceState:
    def __init__(self, path: Path, prices: Optional[Dict[str, PricePoint]] = None) -> None:
        self.path = path
        self.prices = prices or {}

    @classmethod
    def load(cls, path: Path) -> "PriceState":
        if not path.exists():
            return cls(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        prices: Dict[str, PricePoint] = {}
        for name, raw in payload.get("prices", {}).items():
            try:
                prices[name] = PricePoint(
                    typical_price=float(raw["typical_price"]),
                    samples=int(raw.get("samples", 1)),
                    updated_at=str(raw.get("updated_at") or ""),
                )
            except (KeyError, TypeError, ValueError):
                continue
        return cls(path, prices)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "prices": {
                name: {
                    "typical_price": point.typical_price,
                    "samples": point.samples,
                    "updated_at": point.updated_at,
                }
                for name, point in sorted(self.prices.items())
            }
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def update_from_summary(self, summary: Mapping[str, Any], alpha: float = 0.2) -> Tuple[int, int]:
        seen = 0
        updated = 0
        for row in _summary_rows(summary):
            name = str(row.get("name") or "").strip()
            price = _positive_float(row.get("price"))
            if not name or price is None:
                continue
            seen += 1
            existing = self.prices.get(name)
            if existing is None:
                self.prices[name] = PricePoint(price, 1, now_iso())
            else:
                blended = (existing.typical_price * (1 - alpha)) + (price * alpha)
                self.prices[name] = PricePoint(blended, existing.samples + 1, now_iso())
            updated += 1
        return seen, updated

    def lookup(self, name: str, configured: Mapping[str, float], min_samples: int) -> Optional[Tuple[float, str]]:
        if name in configured:
            return configured[name], "configured"
        point = self.prices.get(name)
        if point and point.samples >= min_samples:
            return point.typical_price, "learned"
        return None


def _summary_rows(summary: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    data = summary.get("data", summary)
    if isinstance(data, list):
        for row in data:
            if isinstance(row, Mapping):
                yield row
        return
    if isinstance(data, Mapping):
        for value in data.values():
            if isinstance(value, list):
                for row in value:
                    if isinstance(row, Mapping):
                        yield row


def _positive_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
