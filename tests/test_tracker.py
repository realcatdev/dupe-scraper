import tempfile
import unittest
from pathlib import Path

from dupe_deal_tracker.config import Config
from dupe_deal_tracker.state import PriceState
from dupe_deal_tracker.tracker import collect_baselines, scan_for_deals


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params or {}))
        return self.responses[path]


class TrackerTests(unittest.TestCase):
    def test_scan_uses_configured_typical_price(self):
        with tempfile.TemporaryDirectory() as directory:
            state = PriceState(Path(directory) / "state.json")
            config = Config(
                api_base_url="https://example.invalid",
                api_key="test",
                state_path=state.path,
                deal_threshold=0.85,
                min_profit_usdc=5,
                item_filters=["AK-47"],
                typical_prices={"AK-47 | Redline (Field-Tested)": 50},
            )
            client = FakeClient(
                {
                    "/api/v1/market/get-listings": {
                        "success": True,
                        "data": [
                            {
                                "id": "listing-1",
                                "hash_name": "AK-47 | Redline (Field-Tested)",
                                "price": 38,
                                "category": "BUY_NOW",
                            }
                        ],
                    }
                }
            )

            deals = scan_for_deals(client, config, state)

            self.assertEqual(len(deals), 1)
            self.assertEqual(deals[0].listing.id, "listing-1")
            self.assertEqual(deals[0].source, "configured")
            self.assertAlmostEqual(deals[0].expected_profit, 12)

    def test_collect_baselines_reads_730_summary_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            state = PriceState(Path(directory) / "state.json")
            client = FakeClient(
                {
                    "/api/v1/market/get-all-listings-summary": {
                        "730": [
                            {
                                "name": "M4A1-S | Printstream (Minimal Wear)",
                                "price": 112.5,
                            }
                        ]
                    }
                }
            )

            message = collect_baselines(client, state)

            self.assertIn("1 prices stored", message)
            self.assertIn("M4A1-S | Printstream (Minimal Wear)", state.prices)


if __name__ == "__main__":
    unittest.main()
