from __future__ import annotations

import unittest

from app.classification import categorize, is_investment_relevant
from app.models import MarketSnapshot
from app.scoring import compute_asset_impacts, compute_factor_scores, dashboard_payload


class ScoringTests(unittest.TestCase):
    def test_categorize_macro_events(self) -> None:
        self.assertEqual(categorize("Will the Fed cut interest rates?"), "rates")
        self.assertEqual(categorize("Will CPI inflation be above consensus?"), "inflation")
        self.assertEqual(categorize("Will Brent oil trade above $90?"), "energy")
        self.assertEqual(categorize("Counter-Strike: paiN vs TYLOO"), "other")

    def test_relevance_filter_excludes_non_investment_markets(self) -> None:
        self.assertFalse(is_investment_relevant("Will Algeria win the 2026 FIFA World Cup?"))
        self.assertFalse(is_investment_relevant("Will Iran win the 2026 FIFA World Cup?"))
        self.assertFalse(is_investment_relevant("New Rihanna Album before GTA VI?"))
        self.assertTrue(is_investment_relevant("Will the Fed cut interest rates in September?"))
        self.assertTrue(is_investment_relevant("Will China invade Taiwan before GTA VI?"))

    def test_dashboard_payload_contains_core_sections(self) -> None:
        snapshots = [
            MarketSnapshot(
                platform="test",
                market_id="fed",
                event_id="fed",
                title="Will the Fed cut interest rates?",
                url="",
                category="rates",
                probability=0.65,
                yes_bid=0.64,
                yes_ask=0.66,
                volume=100_000,
                open_interest=80_000,
                liquidity=20_000,
                change_24h=0.05,
            ),
            MarketSnapshot(
                platform="test",
                market_id="cpi",
                event_id="cpi",
                title="Will CPI inflation be above consensus?",
                url="",
                category="inflation",
                probability=0.58,
                yes_bid=0.57,
                yes_ask=0.6,
                volume=90_000,
                open_interest=40_000,
                liquidity=10_000,
                change_24h=0.03,
            ),
        ]

        payload = dashboard_payload(snapshots)

        self.assertEqual(payload["summary"]["marketCount"], 2)
        self.assertGreater(len(payload["factors"]), 0)
        self.assertGreater(len(payload["assetImpacts"]), 0)
        self.assertGreater(len(payload["topEvents"]), 0)

    def test_asset_impacts_are_bounded(self) -> None:
        snapshots = [
            MarketSnapshot(
                platform="test",
                market_id="oil",
                event_id="oil",
                title="Will Brent crude oil trade above $90?",
                url="",
                category="energy",
                probability=0.9,
                yes_bid=0.88,
                yes_ask=0.92,
                volume=1_000_000,
                open_interest=400_000,
                liquidity=120_000,
                change_24h=0.1,
            )
        ]
        factors = compute_factor_scores(snapshots)
        impacts = compute_asset_impacts(factors, snapshots)
        self.assertTrue(all(-1 <= impact.score <= 1 for impact in impacts))


if __name__ == "__main__":
    unittest.main()
