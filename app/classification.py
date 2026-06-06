from __future__ import annotations

import re

from app.models import MarketSnapshot


CATEGORY_LABELS: dict[str, str] = {
    "rates": "利率政策",
    "inflation": "通胀",
    "growth": "增长",
    "politics": "政治政策",
    "geopolitics": "地缘风险",
    "energy": "能源",
    "tech": "科技监管",
    "crypto": "Crypto",
    "markets": "市场价格",
    "other": "其他",
}


CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("rates", ("fed", "fomc", "rate cut", "rate hike", "interest rate", "powell", "ecb", "boe", "yield", "treasury")),
    ("inflation", ("cpi", "inflation", "pce", "ppi", "prices", "tariff", "deflation")),
    ("growth", ("gdp", "recession", "unemployment", "jobs", "payroll", "ism", "pmi", "retail sales")),
    ("politics", ("election", "trump", "biden", "congress", "senate", "policy", "tax", "tariffs", "government shutdown")),
    ("geopolitics", ("war", "ceasefire", "russia", "ukraine", "israel", "iran", "china", "taiwan", "nato", "sanction")),
    ("energy", ("oil", "brent", "wti", "opec", "gas", "lng", "energy", "crude")),
    ("tech", ("ai", "openai", "nvidia", "chip", "semiconductor", "antitrust", "regulation", "data center")),
    ("crypto", ("bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "xrp")),
    ("markets", ("s&p", "spx", "nasdaq", "dow", "stock market", "gold", "silver", "dollar", "yen", "euro")),
]

INVESTMENT_TERMS: tuple[str, ...] = (
    "fed",
    "fomc",
    "rate cut",
    "rate hike",
    "interest rate",
    "treasury",
    "yield",
    "cpi",
    "inflation",
    "pce",
    "ppi",
    "gdp",
    "recession",
    "unemployment",
    "payroll",
    "jobs report",
    "tariff",
    "tariffs",
    "sanction",
    "sanctions",
    "government shutdown",
    "trump",
    "biden",
    "congress",
    "senate",
    "china",
    "taiwan",
    "russia",
    "ukraine",
    "israel",
    "iran",
    "nato",
    "ceasefire",
    "peace deal",
    "war",
    "oil",
    "brent",
    "wti",
    "crude",
    "opec",
    "natural gas",
    "lng",
    "nvidia",
    "semiconductor",
    "chip",
    "ai",
    "antitrust",
    "bitcoin",
    "btc",
    "ethereum",
    "eth",
    "crypto",
    "s&p",
    "spx",
    "nasdaq",
    "dow",
    "dollar",
    "usd",
    "gold",
    "copper",
)

EXCLUDED_TERMS: tuple[str, ...] = (
    "fifa",
    "world cup",
    "soccer",
    "football game",
    "nba",
    "nfl",
    "mlb",
    "nhl",
    "ufc",
    "tennis",
    "counter-strike",
    "dota",
    "league of legends",
    "lpl playoffs",
    "iem cologne",
    "esports",
    "album",
    "gta vi",
    "movie",
    "oscar",
    "grammy",
    "box office",
)


FACTOR_LABELS: dict[str, str] = {
    "risk_appetite": "全球风险偏好",
    "inflation_risk": "通胀压力",
    "fed_hawkishness": "美联储鹰派压力",
    "geopolitical_risk": "地缘政治风险",
    "energy_shock": "能源冲击",
    "policy_uncertainty": "政策不确定性",
    "tech_regulation": "科技监管压力",
    "crypto_sentiment": "Crypto 情绪",
}


FACTOR_WEIGHTS: dict[str, dict[str, float]] = {
    "rates": {
        "risk_appetite": 0.45,
        "fed_hawkishness": -1.0,
    },
    "inflation": {
        "inflation_risk": 1.0,
        "fed_hawkishness": 0.65,
        "risk_appetite": -0.45,
    },
    "growth": {
        "risk_appetite": 0.85,
        "fed_hawkishness": 0.2,
    },
    "politics": {
        "policy_uncertainty": 0.9,
        "risk_appetite": -0.25,
    },
    "geopolitics": {
        "geopolitical_risk": 1.0,
        "policy_uncertainty": 0.4,
        "risk_appetite": -0.7,
    },
    "energy": {
        "energy_shock": 1.0,
        "inflation_risk": 0.45,
        "risk_appetite": -0.35,
    },
    "tech": {
        "tech_regulation": 0.9,
        "policy_uncertainty": 0.25,
        "risk_appetite": -0.25,
    },
    "crypto": {
        "crypto_sentiment": 1.0,
        "risk_appetite": 0.35,
    },
    "markets": {
        "risk_appetite": 0.7,
    },
    "other": {
        "policy_uncertainty": 0.2,
    },
}


ASSET_WEIGHTS: dict[str, dict[str, float]] = {
    "美股": {
        "risk_appetite": 0.9,
        "inflation_risk": -0.45,
        "fed_hawkishness": -0.65,
        "geopolitical_risk": -0.55,
        "energy_shock": -0.25,
        "policy_uncertainty": -0.35,
    },
    "纳斯达克/AI": {
        "risk_appetite": 1.0,
        "fed_hawkishness": -0.85,
        "tech_regulation": -0.9,
        "inflation_risk": -0.45,
    },
    "A股/港股": {
        "risk_appetite": 0.75,
        "geopolitical_risk": -0.45,
        "policy_uncertainty": -0.55,
        "fed_hawkishness": -0.35,
    },
    "美债长端": {
        "risk_appetite": -0.35,
        "inflation_risk": -0.8,
        "fed_hawkishness": -0.75,
        "geopolitical_risk": 0.4,
        "energy_shock": -0.35,
    },
    "美元": {
        "risk_appetite": -0.25,
        "inflation_risk": 0.35,
        "fed_hawkishness": 0.65,
        "geopolitical_risk": 0.4,
    },
    "黄金": {
        "fed_hawkishness": -0.35,
        "inflation_risk": 0.45,
        "geopolitical_risk": 0.75,
        "policy_uncertainty": 0.45,
    },
    "原油": {
        "geopolitical_risk": 0.55,
        "energy_shock": 0.95,
        "risk_appetite": 0.2,
    },
    "铜/工业品": {
        "risk_appetite": 0.75,
        "inflation_risk": 0.25,
        "fed_hawkishness": -0.35,
    },
    "银行": {
        "fed_hawkishness": 0.25,
        "risk_appetite": 0.45,
        "policy_uncertainty": -0.3,
    },
    "地产": {
        "fed_hawkishness": -0.8,
        "inflation_risk": -0.35,
        "risk_appetite": 0.55,
    },
    "能源股": {
        "energy_shock": 0.75,
        "inflation_risk": 0.2,
        "risk_appetite": 0.35,
    },
    "Crypto": {
        "crypto_sentiment": 1.0,
        "risk_appetite": 0.45,
        "fed_hawkishness": -0.5,
        "policy_uncertainty": -0.25,
    },
}


NEGATIVE_EVENT_PATTERNS = (
    "recession",
    "war",
    "attack",
    "shutdown",
    "default",
    "inflation above",
    "cpi above",
    "rate hike",
    "ban",
    "sanction",
    "oil above",
)

RISK_RELIEF_PATTERNS = (
    "ceasefire",
    "peace deal",
    "truce",
    "de-escalation",
    "end the war",
)


POSITIVE_RATES_PATTERNS = (
    "rate cut",
    "cuts",
    "lower rates",
)


def categorize(title: str) -> str:
    text = normalize_text(title)
    for category, words in CATEGORY_KEYWORDS:
        if any(contains_term(text, word) for word in words):
            return category
    return "other"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def contains_term(text: str, term: str) -> bool:
    normalized = normalize_text(text)
    escaped = re.escape(term.lower())
    if re.search(r"[^a-z0-9]", term.lower()):
        return term.lower() in normalized
    return re.search(rf"\b{escaped}\b", normalized) is not None


def is_investment_relevant(text: str) -> bool:
    normalized = normalize_text(text)
    if any(contains_term(normalized, term) for term in EXCLUDED_TERMS):
        # Keep policy/geopolitical variants that happen to mention entertainment only
        # when an explicit macro keyword is also present.
        strong_macro = (
            "fed",
            "cpi",
            "inflation",
            "tariff",
            "tariffs",
            "sanction",
            "sanctions",
            "interest rate",
            "rate cut",
            "rate hike",
            "invade",
            "invades",
            "invasion",
            "war",
            "attack",
            "ceasefire",
            "peace deal",
            "missile",
            "nuclear",
            "airspace",
            "oil",
            "bitcoin",
        )
        if not any(contains_term(normalized, term) for term in strong_macro):
            return False
    return any(contains_term(normalized, term) for term in INVESTMENT_TERMS)


def relevance_score(text: str) -> float:
    normalized = normalize_text(text)
    score = sum(1.0 for term in INVESTMENT_TERMS if contains_term(normalized, term))
    if any(contains_term(normalized, term) for term in ("fed", "cpi", "inflation", "oil", "china", "taiwan", "bitcoin", "nvidia")):
        score += 2.0
    if any(contains_term(normalized, term) for term in EXCLUDED_TERMS):
        score -= 4.0
    return score


def directional_sign(snapshot: MarketSnapshot) -> float:
    text = normalize_text(snapshot.title)
    if any(contains_term(text, pattern) for pattern in RISK_RELIEF_PATTERNS):
        return -1.0
    if snapshot.category == "rates" and any(contains_term(text, pattern) for pattern in POSITIVE_RATES_PATTERNS):
        return 1.0
    if any(contains_term(text, pattern) for pattern in NEGATIVE_EVENT_PATTERNS):
        return -1.0
    return 1.0
