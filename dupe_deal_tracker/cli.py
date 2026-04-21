from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable, List, Optional

from .api import DupeApiError, DupeClient
from .config import Config, load_config
from .models import Deal
from .state import PriceState
from .tracker import collect_baselines, scan_for_deals


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        config = load_config(args.config)
        state = PriceState.load(config.state_path)
        client = DupeClient(config.api_base_url, config.api_key)

        if args.command == "collect-baseline":
            print(collect_baselines(client, state))
            return 0
        if args.command == "scan":
            if args.refresh_baseline:
                print(collect_baselines(client, state))
            return print_deals(scan_for_deals(client, config, state), args.limit)
        if args.command == "daemon":
            return run_daemon(client, config, state, args.limit)
    except (DupeApiError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dupe-deal-tracker",
        description="track Dupe marketplace listings that are cheap versus configured or learned typical prices",
    )
    parser.add_argument("-c", "--config", default="config.json", help="path to config json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("collect-baseline", help="update learned typical prices from Dupe summary data")

    scan = subparsers.add_parser("scan", help="scan current listings for deals")
    scan.add_argument("--refresh-baseline", action="store_true", help="collect summary prices before scanning")
    scan.add_argument("--limit", type=int, default=25, help="maximum deals to print")

    daemon = subparsers.add_parser("daemon", help="continuously refresh baselines and scan")
    daemon.add_argument("--limit", type=int, default=25, help="maximum deals to print per scan")

    return parser


def run_daemon(client: DupeClient, config: Config, state: PriceState, limit: int) -> int:
    last_baseline = 0.0
    while True:
        now = time.monotonic()
        if now - last_baseline >= config.summary_refresh_minutes * 60:
            print(collect_baselines(client, state), flush=True)
            last_baseline = now
        print_deals(scan_for_deals(client, config, state), limit)
        time.sleep(config.scan_interval_seconds)


def print_deals(deals: List[Deal], limit: int) -> int:
    if not deals:
        print("no deals found")
        return 0

    for deal in deals[:limit]:
        listing = deal.listing
        instant = " instant" if listing.instant_fulfill else ""
        float_text = "" if listing.floatvalue is None else f" float={listing.floatvalue:.6f}"
        print(
            f"{deal.expected_profit:>9.2f} usdc profit | "
            f"{deal.discount_percent:>5.1f}% off | "
            f"price={listing.price:.2f} typical={deal.typical_price:.2f} ({deal.source}) | "
            f"{listing.hash_name} | {listing.id}{instant}{float_text}"
        )
    return 0
