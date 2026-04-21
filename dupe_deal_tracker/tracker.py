from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Iterable, List

from .api import DupeClient
from .config import Config
from .models import Deal, Listing
from .state import PriceState


SUMMARY_PATH = "/api/v1/market/get-all-listings-summary"
LISTINGS_PATH = "/api/v1/market/get-listings"


def collect_baselines(client: DupeClient, state: PriceState) -> str:
    payload = client.get(SUMMARY_PATH)
    seen, updated = state.update_from_summary(payload)
    state.save()
    return f"baseline updated: {updated} prices stored from {seen} summary rows"


def scan_for_deals(client: DupeClient, config: Config, state: PriceState) -> List[Deal]:
    listings = _fetch_candidate_listings(client, config)
    deals: List[Deal] = []
    for listing in listings:
        lookup = state.lookup(
            listing.hash_name,
            configured=config.typical_prices,
            min_samples=config.min_samples_for_learned_price,
        )
        if lookup is None:
            continue
        typical, source = lookup
        if typical <= 0:
            continue
        expected_profit = typical - listing.price
        ratio = listing.price / typical
        if ratio <= config.deal_threshold and expected_profit >= config.min_profit_usdc:
            deals.append(
                Deal(
                    listing=listing,
                    typical_price=typical,
                    discount_percent=(1 - ratio) * 100,
                    expected_profit=expected_profit,
                    source=source,
                )
            )
    return sorted(deals, key=lambda deal: (-deal.expected_profit, deal.listing.price))


def _fetch_candidate_listings(client: DupeClient, config: Config) -> List[Listing]:
    filters = config.item_filters or [None]
    all_listings: Dict[str, Listing] = {}
    for item_filter in filters:
        params: Dict[str, Any] = {
            "limit": min(config.listing_limit, 500),
            "offset": 0,
            "category": "BUY_NOW",
            "min_price": config.min_price_usdc,
            "max_price": config.max_price_usdc,
            "sort_by": "price_asc",
        }
        if item_filter:
            params["item_name"] = item_filter
        payload = client.get(LISTINGS_PATH, params)
        for listing in _listings_from_payload(payload):
            if listing.id:
                all_listings[listing.id] = listing
    return list(all_listings.values())


def _listings_from_payload(payload: Mapping[str, Any]) -> Iterable[Listing]:
    data = payload.get("data", [])
    if not isinstance(data, list):
        return []
    return [Listing.from_api(row) for row in data if isinstance(row, Mapping)]
