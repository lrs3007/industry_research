from __future__ import annotations

import json
import logging
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.classification import categorize, is_investment_relevant, relevance_score
from app.models import MarketSnapshot, utc_now_iso

LOGGER = logging.getLogger(__name__)

POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"
KALSHI_API = "https://external-api.kalshi.com/trade-api/v2"
USER_AGENT = "industry-research-sentiment-barometer/0.1"


class CollectorError(RuntimeError):
    pass


def fetch_json(url: str, timeout: float = 12.0, attempts: int = 3) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.4 * (attempt + 1))
    raise CollectorError(f"Could not fetch {url}: {last_error}") from last_error


def collect_polymarket(limit: int = 120) -> list[MarketSnapshot]:
    raw_limit = min(1000, max(300, limit * 8))
    params = urllib.parse.urlencode(
        {
            "active": "true",
            "closed": "false",
            "limit": str(raw_limit),
            "order": "volume24hr",
            "ascending": "false",
        }
    )
    data = fetch_json(f"{POLYMARKET_GAMMA}/markets?{params}")
    rows = data if isinstance(data, list) else data.get("markets", [])
    observed_at = utc_now_iso()
    markets: list[MarketSnapshot] = []
    for row in rows:
        snapshot = _parse_polymarket_market(row, observed_at)
        if snapshot and _is_relevant_snapshot(snapshot, row):
            markets.append(snapshot)
    return _rank_relevant(markets)[:limit]


def collect_kalshi(limit: int = 120) -> list[MarketSnapshot]:
    raw_limit = min(1000, max(300, limit * 8))
    params = urllib.parse.urlencode(
        {
            "status": "open",
            "limit": str(raw_limit),
        }
    )
    data = fetch_json(f"{KALSHI_API}/markets?{params}")
    rows = data.get("markets", []) if isinstance(data, dict) else []
    observed_at = utc_now_iso()
    markets: list[MarketSnapshot] = []
    for row in rows:
        snapshot = _parse_kalshi_market(row, observed_at)
        if snapshot and _is_relevant_snapshot(snapshot, row):
            markets.append(snapshot)
    return _rank_relevant(markets)[:limit]


def collect_all(limit: int = 120) -> tuple[list[MarketSnapshot], list[str]]:
    errors: list[str] = []
    markets: list[MarketSnapshot] = []
    for name, collector in (("polymarket", collect_polymarket), ("kalshi", collect_kalshi)):
        try:
            markets.extend(collector(limit=limit))
        except CollectorError as exc:
            LOGGER.warning("%s collector failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    return markets, errors


def _parse_polymarket_market(row: dict[str, Any], observed_at: str) -> MarketSnapshot | None:
    title = _first_text(row, "question", "title", "description")
    if not title:
        return None
    probability = _polymarket_probability(row)
    if probability is None:
        return None
    market_id = str(row.get("conditionId") or row.get("id") or row.get("slug") or title)
    slug = row.get("slug") or ""
    url = f"https://polymarket.com/market/{slug}" if slug else "https://polymarket.com"
    yes_bid = _price(row.get("bestBid") or row.get("yesBid"))
    yes_ask = _price(row.get("bestAsk") or row.get("yesAsk"))
    return MarketSnapshot(
        platform="polymarket",
        market_id=market_id,
        event_id=str(row.get("eventSlug") or row.get("groupItemTitle") or slug or market_id),
        title=title,
        url=url,
        category=categorize(title),
        probability=probability,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        volume=_number(row, "volume24hr", "volumeNum", "volume"),
        open_interest=_number(row, "openInterest", "openInterestNum"),
        liquidity=_number(row, "liquidityNum", "liquidity"),
        close_time=_first_text(row, "endDate", "endDateIso", "end_date"),
        observed_at=observed_at,
        raw=_trim_raw(row),
        change_24h=_signed_number(row, "oneDayPriceChange", "oneHourPriceChange"),
        change_7d=_signed_number(row, "oneWeekPriceChange", "oneMonthPriceChange"),
    )


def _parse_kalshi_market(row: dict[str, Any], observed_at: str) -> MarketSnapshot | None:
    title = _first_text(row, "title", "subtitle", "ticker")
    if not title:
        return None
    yes_bid = _kalshi_cent_price(row.get("yes_bid") or row.get("yes_bid_dollars"))
    yes_ask = _kalshi_cent_price(row.get("yes_ask") or row.get("yes_ask_dollars"))
    last_price = _kalshi_cent_price(row.get("last_price") or row.get("last_price_dollars"))
    if yes_bid is not None and yes_ask is not None and yes_ask >= yes_bid:
        probability = (yes_bid + yes_ask) / 2
    elif last_price is not None:
        probability = last_price
    else:
        return None
    ticker = str(row.get("ticker") or title)
    event_ticker = str(row.get("event_ticker") or ticker)
    return MarketSnapshot(
        platform="kalshi",
        market_id=ticker,
        event_id=event_ticker,
        title=title,
        url=f"https://kalshi.com/markets/{event_ticker.lower()}",
        category=categorize(title),
        probability=probability,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        volume=_number(row, "volume", "volume_24h", "volume_fp", "volume_24h_fp"),
        open_interest=_number(row, "open_interest", "open_interest_fp"),
        liquidity=_number(row, "liquidity", "liquidity_dollars"),
        close_time=_first_text(row, "close_time", "expiration_time"),
        observed_at=observed_at,
        raw=_trim_raw(row),
        change_24h=_kalshi_change(row),
        change_7d=0.0,
    )


def _polymarket_probability(row: dict[str, Any]) -> float | None:
    for key in ("lastTradePrice", "lastPrice", "bestAsk", "bestBid"):
        parsed = _price(row.get(key))
        if parsed is not None:
            return parsed
    outcomes = _maybe_json_list(row.get("outcomes"))
    prices = _maybe_json_list(row.get("outcomePrices"))
    if outcomes and prices and len(outcomes) == len(prices):
        for outcome, price in zip(outcomes, prices, strict=False):
            if str(outcome).lower() == "yes":
                return _price(price)
        return _price(prices[0])
    return None


def _maybe_json_list(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, list) else None
        except json.JSONDecodeError:
            return None
    return None


def _price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if parsed > 1:
        parsed = parsed / 100
    return min(1.0, max(0.0, parsed))


def _kalshi_cent_price(value: Any) -> float | None:
    parsed = _price(value)
    if parsed is None:
        return None
    return parsed


def _number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            return max(0.0, parsed)
    return 0.0


def _signed_number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            if abs(parsed) > 1:
                parsed = parsed / 100
            return parsed
    return 0.0


def _kalshi_change(row: dict[str, Any]) -> float:
    current = _kalshi_cent_price(row.get("last_price") or row.get("last_price_dollars"))
    previous = _kalshi_cent_price(row.get("previous_price") or row.get("previous_price_dollars"))
    if current is None or previous is None:
        return 0.0
    return current - previous


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return ""


def _trim_raw(row: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "ticker",
        "event_ticker",
        "conditionId",
        "id",
        "slug",
        "question",
        "title",
        "volume",
        "volume24hr",
        "open_interest",
        "openInterest",
        "liquidity",
        "liquidityNum",
        "yes_bid_dollars",
        "yes_ask_dollars",
        "last_price_dollars",
        "oneDayPriceChange",
        "oneWeekPriceChange",
    }
    return {key: value for key, value in row.items() if key in allowed}


def _is_relevant_snapshot(snapshot: MarketSnapshot, row: dict[str, Any]) -> bool:
    text = " ".join(
        str(value)
        for value in (
            snapshot.title,
            row.get("description", ""),
            row.get("slug", ""),
            row.get("event_ticker", ""),
            row.get("ticker", ""),
            _event_titles(row),
        )
        if value
    )
    return is_investment_relevant(text)


def _event_titles(row: dict[str, Any]) -> str:
    events = row.get("events")
    if not isinstance(events, list):
        return ""
    return " ".join(str(event.get("title", "")) for event in events if isinstance(event, dict))


def _rank_relevant(markets: list[MarketSnapshot]) -> list[MarketSnapshot]:
    return sorted(
        markets,
        key=lambda item: (
            relevance_score(item.title),
            item.volume + item.open_interest + item.liquidity,
            abs(item.change_24h),
        ),
        reverse=True,
    )
