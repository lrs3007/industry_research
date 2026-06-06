from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean

from app.classification import ASSET_WEIGHTS, FACTOR_LABELS, FACTOR_WEIGHTS, CATEGORY_LABELS, directional_sign, is_investment_relevant
from app.models import AssetImpact, FactorScore, MarketSnapshot


def liquidity_confidence(snapshot: MarketSnapshot) -> float:
    activity = math.log10(max(1.0, snapshot.volume + snapshot.open_interest + snapshot.liquidity))
    activity_score = min(1.0, activity / 7.0)
    spread_penalty = max(0.25, 1.0 - min(0.5, snapshot.spread) * 1.8)
    platform_floor = 0.7 if snapshot.platform in {"polymarket", "kalshi"} else 0.45
    return round(max(0.05, activity_score * spread_penalty * platform_floor), 4)


def event_signal(snapshot: MarketSnapshot) -> float:
    probability_component = (snapshot.probability - 0.5) * 2
    momentum_component = snapshot.change_24h * 4 + snapshot.change_7d * 1.5
    signed = directional_sign(snapshot) * (0.65 * probability_component + 0.35 * momentum_component)
    return signed * liquidity_confidence(snapshot)


def compute_factor_scores(snapshots: list[MarketSnapshot]) -> list[FactorScore]:
    buckets: dict[str, list[tuple[MarketSnapshot, float]]] = defaultdict(list)
    for snapshot in snapshots:
        signal = event_signal(snapshot)
        for factor, weight in FACTOR_WEIGHTS.get(snapshot.category, FACTOR_WEIGHTS["other"]).items():
            buckets[factor].append((snapshot, signal * weight))

    factors: list[FactorScore] = []
    for key, entries in buckets.items():
        raw = sum(value for _, value in entries)
        confidence = mean(liquidity_confidence(snapshot) for snapshot, _ in entries)
        average_probability = mean(snapshot.probability for snapshot, _ in entries)
        momentum = mean(snapshot.change_24h for snapshot, _ in entries)
        score = clamp_score(raw / max(1.0, math.sqrt(len(entries))))
        factors.append(
            FactorScore(
                key=key,
                label=FACTOR_LABELS.get(key, key),
                score=score,
                probability=average_probability,
                confidence=confidence,
                momentum=momentum,
                event_count=len(entries),
            )
        )
    for key, label in FACTOR_LABELS.items():
        if key not in buckets:
            factors.append(FactorScore(key=key, label=label, score=0.0, probability=0.0, confidence=0.0, momentum=0.0, event_count=0))
    return sorted(factors, key=lambda item: abs(item.score), reverse=True)


def compute_asset_impacts(factors: list[FactorScore], snapshots: list[MarketSnapshot]) -> list[AssetImpact]:
    factor_map = {item.key: item for item in factors}
    top_by_category: dict[str, list[MarketSnapshot]] = defaultdict(list)
    for snapshot in sorted(snapshots, key=lambda item: abs(event_signal(item)), reverse=True):
        if len(top_by_category[snapshot.category]) < 2:
            top_by_category[snapshot.category].append(snapshot)

    impacts: list[AssetImpact] = []
    for asset, weights in ASSET_WEIGHTS.items():
        raw = 0.0
        confidence_values = []
        for factor_key, weight in weights.items():
            factor = factor_map.get(factor_key)
            if factor is None:
                continue
            raw += factor.score * weight
            confidence_values.append(factor.confidence)
        confidence = mean(confidence_values) if confidence_values else 0.0
        contributors = _contributors_for_asset(asset, top_by_category)
        impacts.append(AssetImpact(asset=asset, score=clamp_score(raw / max(1.0, math.sqrt(len(weights)))), confidence=confidence, contributors=contributors))
    return sorted(impacts, key=lambda item: item.score, reverse=True)


def detect_divergences(snapshots: list[MarketSnapshot]) -> list[dict[str, object]]:
    groups: dict[str, list[MarketSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        key = _normalized_event_key(snapshot)
        groups[key].append(snapshot)

    divergences: list[dict[str, object]] = []
    for key, rows in groups.items():
        platforms = {row.platform for row in rows}
        if len(platforms) < 2:
            continue
        highest = max(rows, key=lambda item: item.probability)
        lowest = min(rows, key=lambda item: item.probability)
        spread = highest.probability - lowest.probability
        if spread >= 0.08:
            divergences.append(
                {
                    "key": key,
                    "title": highest.title,
                    "spread": spread,
                    "highPlatform": highest.platform,
                    "highProbability": highest.probability,
                    "lowPlatform": lowest.platform,
                    "lowProbability": lowest.probability,
                }
            )
    return sorted(divergences, key=lambda item: float(item["spread"]), reverse=True)


def dashboard_payload(snapshots: list[MarketSnapshot], errors: list[str] | None = None) -> dict[str, object]:
    snapshots = _investment_snapshots(snapshots)
    factors = compute_factor_scores(snapshots)
    impacts = compute_asset_impacts(factors, snapshots)
    ranked = sorted(snapshots, key=lambda item: (abs(event_signal(item)), liquidity_confidence(item)), reverse=True)
    return {
        "generatedAt": max((item.observed_at for item in snapshots), default=""),
        "status": "demo" if snapshots and all(item.platform == "demo" for item in snapshots) else "live",
        "errors": errors or [],
        "summary": {
            "marketCount": len(snapshots),
            "platforms": sorted({item.platform for item in snapshots}),
            "averageConfidence": mean([liquidity_confidence(item) for item in snapshots]) if snapshots else 0.0,
            "categoryCounts": _category_counts(snapshots),
        },
        "factors": [_factor_to_dict(item) for item in factors],
        "assetImpacts": [_asset_to_dict(item) for item in impacts],
        "topEvents": [_snapshot_to_dict(item) for item in ranked[:24]],
        "divergences": detect_divergences(snapshots),
        "heatmap": _heatmap(factors),
    }


def clamp_score(value: float) -> float:
    return round(max(-1.0, min(1.0, value)), 4)


def _factor_to_dict(item: FactorScore) -> dict[str, object]:
    return {
        "key": item.key,
        "label": item.label,
        "score": item.score,
        "probability": item.probability,
        "confidence": item.confidence,
        "momentum": item.momentum,
        "eventCount": item.event_count,
    }


def _asset_to_dict(item: AssetImpact) -> dict[str, object]:
    return {
        "asset": item.asset,
        "score": item.score,
        "confidence": item.confidence,
        "contributors": item.contributors,
    }


def _snapshot_to_dict(item: MarketSnapshot) -> dict[str, object]:
    return {
        "platform": item.platform,
        "marketId": item.market_id,
        "eventId": item.event_id,
        "title": item.title,
        "url": item.url,
        "category": item.category,
        "categoryLabel": CATEGORY_LABELS.get(item.category, item.category),
        "probability": item.probability,
        "change24h": item.change_24h,
        "change7d": item.change_7d,
        "volume": item.volume,
        "openInterest": item.open_interest,
        "liquidity": item.liquidity,
        "spread": item.spread,
        "confidence": liquidity_confidence(item),
        "signal": event_signal(item),
        "observedAt": item.observed_at,
    }


def _category_counts(snapshots: list[MarketSnapshot]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for snapshot in snapshots:
        counts[CATEGORY_LABELS.get(snapshot.category, snapshot.category)] += 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def _heatmap(factors: list[FactorScore]) -> list[dict[str, object]]:
    factor_map = {item.key: item.score for item in factors}
    rows = []
    for asset, weights in ASSET_WEIGHTS.items():
        cells = []
        for factor_key, weight in weights.items():
            cells.append(
                {
                    "factor": FACTOR_LABELS.get(factor_key, factor_key),
                    "score": clamp_score(factor_map.get(factor_key, 0.0) * weight),
                }
            )
        rows.append({"asset": asset, "cells": cells})
    return rows


def _contributors_for_asset(asset: str, top_by_category: dict[str, list[MarketSnapshot]]) -> list[str]:
    if asset in {"原油", "能源股"}:
        categories = ("energy", "geopolitics", "inflation")
    elif asset in {"纳斯达克/AI"}:
        categories = ("tech", "rates", "inflation", "crypto")
    elif asset in {"美元", "美债长端", "黄金"}:
        categories = ("rates", "inflation", "geopolitics")
    elif asset == "Crypto":
        categories = ("crypto", "rates", "policy")
    else:
        categories = ("growth", "politics", "geopolitics", "rates")
    contributors: list[str] = []
    for category in categories:
        contributors.extend(item.title for item in top_by_category.get(category, []))
    return contributors[:3]


def _normalized_event_key(snapshot: MarketSnapshot) -> str:
    words = [
        word
        for word in snapshot.title.lower().replace("?", "").replace(",", "").split()
        if len(word) > 3 and word not in {"will", "what", "when", "market", "before", "after", "this", "that"}
    ]
    return " ".join(words[:6])


def _investment_snapshots(snapshots: list[MarketSnapshot]) -> list[MarketSnapshot]:
    filtered = [
        snapshot
        for snapshot in snapshots
        if snapshot.platform in {"demo", "test"} or is_investment_relevant(f"{snapshot.title} {snapshot.event_id} {snapshot.market_id}")
    ]
    return filtered or snapshots
