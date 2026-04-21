from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class Config:
    api_base_url: str
    api_key: str
    state_path: Path
    deal_threshold: float = 0.82
    min_profit_usdc: float = 5.0
    min_price_usdc: float = 1.0
    max_price_usdc: float = 1_000_000.0
    listing_limit: int = 250
    summary_refresh_minutes: int = 5
    scan_interval_seconds: int = 60
    min_samples_for_learned_price: int = 3
    item_filters: List[str] = field(default_factory=list)
    typical_prices: Dict[str, float] = field(default_factory=dict)


def load_config(path: Optional[str], api_key_override: Optional[str] = None) -> Config:
    raw: Dict[str, Any] = {}
    if path:
        config_path = Path(path)
        if config_path.exists():
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        elif path != "config.json":
            raise FileNotFoundError(f"config file not found: {path}")
        else:
            raw = {}

    api_key_env = str(raw.get("api_key_env") or "DUPE_API_KEY")
    api_key = str(api_key_override or raw.get("api_key") or os.environ.get(api_key_env) or "")
    if not api_key:
        raise ValueError(f"set an api key in ${api_key_env} or config field api_key")

    api_base_url = str(raw.get("api_base_url") or os.environ.get("DUPE_API_BASE_URL") or "https://dupe.com")
    state_path = Path(str(raw.get("state_path") or ".dupe_deals/state.json"))

    return Config(
        api_base_url=api_base_url,
        api_key=api_key,
        state_path=state_path,
        deal_threshold=_float(raw, "deal_threshold", 0.82),
        min_profit_usdc=_float(raw, "min_profit_usdc", 5.0),
        min_price_usdc=_float(raw, "min_price_usdc", 1.0),
        max_price_usdc=_float(raw, "max_price_usdc", 1_000_000.0),
        listing_limit=_int(raw, "listing_limit", 250),
        summary_refresh_minutes=_int(raw, "summary_refresh_minutes", 5),
        scan_interval_seconds=_int(raw, "scan_interval_seconds", 60),
        min_samples_for_learned_price=_int(raw, "min_samples_for_learned_price", 3),
        item_filters=[str(item) for item in raw.get("item_filters", [])],
        typical_prices=_typical_prices(raw.get("typical_prices", {})),
    )


def _float(raw: Mapping[str, Any], key: str, default: float) -> float:
    value = raw.get(key, default)
    return float(value)


def _int(raw: Mapping[str, Any], key: str, default: int) -> int:
    value = raw.get(key, default)
    return int(value)


def _typical_prices(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    prices: Dict[str, float] = {}
    for name, value in raw.items():
        try:
            prices[str(name)] = float(value)
        except (TypeError, ValueError):
            continue
    return prices
