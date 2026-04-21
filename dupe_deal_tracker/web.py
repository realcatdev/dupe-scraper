from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from .api import DupeApiError, DupeClient
from .config import Config, load_config
from .models import Deal
from .state import PriceState
from .tracker import collect_baselines, scan_for_deals


STATIC_DIR = Path(__file__).with_name("static")


def run_web_app(config_path: str, host: str, port: int) -> int:
    server = ThreadingHTTPServer((host, port), _handler(config_path))
    print(f"dupe deal tracker web app running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping web app")
    finally:
        server.server_close()
    return 0


def _handler(config_path: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
                return
            if parsed.path.startswith("/static/"):
                self._send_static(parsed.path.removeprefix("/static/"))
                return
            if parsed.path == "/api/status":
                self._status()
                return
            if parsed.path == "/api/scan":
                self._scan(parse_qs(parsed.query))
                return
            if parsed.path == "/api/baseline":
                self._baseline()
                return
            self._json({"success": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _status(self) -> None:
            try:
                config = load_config(config_path, _api_key_override(self))
                state = PriceState.load(config.state_path)
                self._json(
                    {
                        "success": True,
                        "config": _config_payload(config),
                        "learned_prices": len(state.prices),
                    }
                )
            except (FileNotFoundError, ValueError) as exc:
                self._json({"success": False, "error": str(exc)}, HTTPStatus.OK)

        def _scan(self, query: Dict[str, List[str]]) -> None:
            try:
                config, state, client = _runtime(config_path, _api_key_override(self))
                message = None
                if query.get("refresh", ["0"])[0] in {"1", "true", "yes"}:
                    message = collect_baselines(client, state)
                deals = scan_for_deals(client, config, state)
                self._json(
                    {
                        "success": True,
                        "message": message,
                        "deals": [_deal_payload(deal) for deal in deals],
                        "config": _config_payload(config),
                        "learned_prices": len(state.prices),
                    }
                )
            except (DupeApiError, FileNotFoundError, ValueError) as exc:
                self._json({"success": False, "error": str(exc)}, HTTPStatus.OK)

        def _baseline(self) -> None:
            try:
                config, state, client = _runtime(config_path, _api_key_override(self))
                message = collect_baselines(client, state)
                self._json(
                    {
                        "success": True,
                        "message": message,
                        "config": _config_payload(config),
                        "learned_prices": len(state.prices),
                    }
                )
            except (DupeApiError, FileNotFoundError, ValueError) as exc:
                self._json({"success": False, "error": str(exc)}, HTTPStatus.OK)

        def _send_static(self, name: str) -> None:
            allowed = {
                "app.css": "text/css; charset=utf-8",
                "app.js": "application/javascript; charset=utf-8",
            }
            if name not in allowed:
                self._json({"success": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_file(STATIC_DIR / name, allowed[name])

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                body = path.read_bytes()
            except FileNotFoundError:
                self._json({"success": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _runtime(config_path: str, api_key_override: str | None) -> tuple[Config, PriceState, DupeClient]:
    config = load_config(config_path, api_key_override)
    state = PriceState.load(config.state_path)
    client = DupeClient(config.api_base_url, config.api_key)
    return config, state, client


def _api_key_override(handler: BaseHTTPRequestHandler) -> str | None:
    api_key = handler.headers.get("x-dupe-api-key", "").strip()
    return api_key or None


def _config_payload(config: Config) -> Dict[str, Any]:
    return {
        "api_base_url": config.api_base_url,
        "deal_threshold": config.deal_threshold,
        "min_profit_usdc": config.min_profit_usdc,
        "min_price_usdc": config.min_price_usdc,
        "max_price_usdc": config.max_price_usdc,
        "listing_limit": config.listing_limit,
        "summary_refresh_minutes": config.summary_refresh_minutes,
        "scan_interval_seconds": config.scan_interval_seconds,
        "min_samples_for_learned_price": config.min_samples_for_learned_price,
        "item_filters": config.item_filters,
        "configured_prices": len(config.typical_prices),
    }


def _deal_payload(deal: Deal) -> Dict[str, Any]:
    listing = deal.listing
    return {
        "id": listing.id,
        "hash_name": listing.hash_name,
        "item_name": listing.item_name,
        "price": listing.price,
        "typical_price": deal.typical_price,
        "discount_percent": deal.discount_percent,
        "expected_profit": deal.expected_profit,
        "source": deal.source,
        "category": listing.category,
        "asset_id": listing.asset_id,
        "floatvalue": listing.floatvalue,
        "instant_fulfill": listing.instant_fulfill,
    }
