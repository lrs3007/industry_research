#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_payload(refresh: bool, limit: int) -> dict[str, Any]:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.server import current_payload, refresh_payload
    from app.store import DEFAULT_DB_PATH

    db_path = root / DEFAULT_DB_PATH
    if refresh:
        return refresh_payload(db_path, limit=limit)
    return current_payload(db_path)


def _top(rows: list[dict[str, Any]], count: int, score_key: str = "score") -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: abs(float(row.get(score_key, 0) or 0)), reverse=True)[:count]


def _compact(payload: dict[str, Any], count: int) -> dict[str, Any]:
    return {
        "generatedAt": payload.get("generatedAt"),
        "status": payload.get("status"),
        "errors": payload.get("errors", []),
        "summary": payload.get("summary", {}),
        "factors": _top(list(payload.get("factors", [])), count),
        "assetImpacts": _top(list(payload.get("assetImpacts", [])), count),
        "topEvents": list(payload.get("topEvents", []))[: max(count, 8)],
        "divergences": list(payload.get("divergences", []))[:count],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print compact dashboard signals for the industry stock selection skill.")
    parser.add_argument("--refresh", action="store_true", help="Collect fresh Polymarket/Kalshi data before summarizing.")
    parser.add_argument("--limit", type=int, default=160, help="Maximum live markets to collect per platform.")
    parser.add_argument("--count", type=int, default=8, help="Number of top factors/assets/events to print.")
    args = parser.parse_args()

    payload = _load_payload(refresh=args.refresh, limit=args.limit)
    print(json.dumps(_compact(payload, count=max(1, args.count)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
