from __future__ import annotations

import re


PLATFORM_LABELS: dict[str, str] = {
    "demo": "演示数据",
    "test": "测试数据",
    "polymarket": "Polymarket",
    "kalshi": "Kalshi",
}

MONTH_LABELS: dict[str, str] = {
    "January": "1月",
    "February": "2月",
    "March": "3月",
    "April": "4月",
    "May": "5月",
    "June": "6月",
    "July": "7月",
    "August": "8月",
    "September": "9月",
    "October": "10月",
    "November": "11月",
    "December": "12月",
}

ENTITY_LABELS: dict[str, str] = {
    "Bitcoin": "比特币",
    "Ethereum": "以太坊",
    "China": "中国",
    "Taiwan": "台湾",
    "Israel": "以色列",
    "Iran": "伊朗",
    "Lebanon": "黎巴嫩",
    "NATO": "北约",
    "Donald Trump": "唐纳德·特朗普",
    "Trump": "特朗普",
    "Hunter Biden": "亨特·拜登",
}


TITLE_TRANSLATIONS: dict[str, str] = {
    "Will the Federal Reserve cut interest rates by September?": "美联储会在9月前降息吗？",
    "Will next US CPI inflation print above consensus?": "美国下一次消费者物价指数会高于市场预期吗？",
    "Will Brent crude oil trade above $90 this quarter?": "本季度布伦特原油价格会高于 90 美元吗？",
    "Will a major Russia-Ukraine ceasefire agreement be announced this month?": "本月会宣布重大的俄乌停火协议吗？",
    "Will the US announce major artificial intelligence regulation before year end?": "美国会在年底前宣布重大人工智能监管政策吗？",
    "Will the US announce major AI regulation before year end?": "美国会在年底前宣布重大人工智能监管政策吗？",
    "Will Bitcoin trade above $120,000 before July?": "比特币会在7月前突破 12 万美元吗？",
    "Will new US tariff policy be announced this quarter?": "美国本季度会宣布新的关税政策吗？",
    "Will the US enter a recession this year?": "美国今年会陷入衰退吗？",
    "Will the Fed cut interest rates?": "美联储会降息吗？",
    "Will CPI inflation be above consensus?": "消费者物价指数会高于市场预期吗？",
    "Will Brent oil trade above $90?": "布伦特原油价格会高于 90 美元吗？",
    "Will Hunter Biden win the 2028 Democratic presidential nomination?": "亨特·拜登会赢得2028年民主党总统候选人提名吗？",
}


TERM_TRANSLATIONS: tuple[tuple[str, str], ...] = (
    ("the Federal Reserve", "美联储"),
    ("Federal Reserve", "美联储"),
    ("interest rates", "利率"),
    ("interest rate", "利率"),
    ("rate cuts", "降息"),
    ("rate cut", "降息"),
    ("rate hikes", "加息"),
    ("rate hike", "加息"),
    ("above consensus", "高于市场预期"),
    ("below consensus", "低于市场预期"),
    ("recession", "衰退"),
    ("inflation", "通胀"),
    ("tariff policy", "关税政策"),
    ("tariffs", "关税"),
    ("tariff", "关税"),
    ("ceasefire agreement", "停火协议"),
    ("ceasefire", "停火"),
    ("peace deal", "和平协议"),
    ("geopolitical", "地缘政治"),
    ("regulation", "监管"),
    ("announces", "宣布"),
    ("announce", "宣布"),
    ("extension", "延期"),
    ("agreement", "协议"),
    ("permanent", "永久"),
    ("withdraw", "退出"),
    ("invade", "入侵"),
    ("President", "总统"),
    ("Democratic presidential nomination", "民主党总统候选人提名"),
    ("United States", "美国"),
    ("Strait of Hormuz", "霍尔木兹海峡"),
    ("trade above", "价格高于"),
    ("trade below", "价格低于"),
    ("Brent crude oil", "布伦特原油"),
    ("Brent oil", "布伦特原油"),
    ("crude oil", "原油"),
    ("oil", "石油"),
    ("Bitcoin", "比特币"),
    ("Ethereum", "以太坊"),
    ("crypto", "加密资产"),
    ("artificial intelligence", "人工智能"),
    ("Nvidia", "英伟达"),
    ("semiconductor", "半导体"),
    ("AI", "人工智能"),
    ("CPI", "消费者物价指数"),
    ("PCE", "个人消费支出价格指数"),
    ("PPI", "生产者价格指数"),
    ("GDP", "国内生产总值"),
    ("Fed", "美联储"),
    ("US", "美国"),
    ("U.S.", "美国"),
    ("China", "中国"),
    ("Taiwan", "台湾"),
    ("Russia", "俄罗斯"),
    ("Ukraine", "乌克兰"),
    ("Israel", "以色列"),
    ("Iran", "伊朗"),
    ("NATO", "北约"),
    ("before", "前"),
    ("after", "后"),
    ("by", "在"),
    ("this quarter", "本季度"),
    ("this year", "今年"),
    ("this month", "本月"),
    ("year end", "年底"),
    ("September", "9月"),
    ("July", "7月"),
)


ERROR_TRANSLATIONS: tuple[tuple[str, str], ...] = (
    ("No live markets were collected; using latest local snapshots.", "未采集到实时市场，正在使用最近一次本地快照。"),
    ("No live markets were collected; using demo dataset.", "未采集到实时市场，正在使用演示数据集。"),
)


def platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


def translate_market_title(title: str) -> str:
    normalized = " ".join(title.strip().split())
    if not normalized:
        return normalized
    if normalized in TITLE_TRANSLATIONS:
        return TITLE_TRANSLATIONS[normalized]
    if re.search(r"[\u4e00-\u9fff]", normalized):
        return normalized

    pattern_translation = _translate_market_title_pattern(normalized)
    if pattern_translation:
        return pattern_translation

    translated = normalized
    starts_with_will = bool(re.match(r"^will\b", translated, flags=re.IGNORECASE))
    translated = re.sub(r"^will\s+", "", translated, flags=re.IGNORECASE)
    translated = translated.rstrip("?")
    translated = _replace_terms(translated)
    translated = _polish_translated_title(translated)
    if starts_with_will:
        return f"{translated}吗？"
    if normalized.endswith("?"):
        return f"{translated}？"
    return translated


def translate_error_message(message: str) -> str:
    for source, replacement in ERROR_TRANSLATIONS:
        if message == source:
            return replacement
    return (
        message.replace("polymarket:", "Polymarket 采集失败：")
        .replace("kalshi:", "Kalshi 采集失败：")
        .replace("Could not fetch", "无法获取")
    )


def _replace_terms(value: str) -> str:
    translated = value
    for source, target in sorted(TERM_TRANSLATIONS, key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)
    return translated


def _translate_market_title_pattern(title: str) -> str | None:
    match = re.fullmatch(r"Bitcoin Up or Down on (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"比特币在{_translate_date(match['date'])}上涨还是下跌？"

    match = re.fullmatch(r"Will the price of (?P<asset>Bitcoin|Ethereum) be above \$(?P<price>[0-9,]+) on (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"{_entity_label(match['asset'])}价格会在{_translate_date(match['date'])}高于 {match['price']} 美元吗？"

    match = re.fullmatch(r"(?P<country>Israel) announces (?P<region>Lebanon) ceasefire extension by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"{_entity_label(match['country'])}会在{_translate_date(match['date'])}前宣布延长{_entity_label(match['region'])}停火吗？"

    match = re.fullmatch(r"US announces new Iran agreement/ceasefire extension by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"美国会在{_translate_date(match['date'])}前宣布新的伊朗协议或停火延期吗？"

    match = re.fullmatch(r"US x Iran permanent peace deal by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"美国和伊朗会在{_translate_date(match['date'])}前达成永久和平协议吗？"

    match = re.fullmatch(r"Will the Fed (?P<direction>increase|decrease) interest rates by (?P<size>[0-9+]+) bps after the (?P<meeting>.+) meeting\?", title, flags=re.IGNORECASE)
    if match:
        action = "加息" if match["direction"].lower() == "increase" else "降息"
        return f"美联储会在{_translate_date(match['meeting'])}会议后{action} {match['size']} 个基点吗？"

    match = re.fullmatch(r"Will there be no change in Fed interest rates after the (?P<meeting>.+) meeting\?", title, flags=re.IGNORECASE)
    if match:
        return f"美联储会在{_translate_date(match['meeting'])}会议后维持利率不变吗？"

    match = re.fullmatch(r"Will Donald Trump announce that the United States blockade of the Strait of Hormuz has been lifted by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"唐纳德·特朗普会在{_translate_date(match['date'])}前宣布美国解除对霍尔木兹海峡的封锁吗？"

    match = re.fullmatch(r"Trump out as President by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"特朗普会在{_translate_date(match['date'])}前卸任总统吗？"

    match = re.fullmatch(r"Will (?P<country>China) invade (?P<target>Taiwan) by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"{_entity_label(match['country'])}会在{_translate_date(match['date'])}前入侵{_entity_label(match['target'])}吗？"

    match = re.fullmatch(r"Will US withdraw from NATO by (?P<date>.+)\?", title, flags=re.IGNORECASE)
    if match:
        return f"美国会在{_translate_date(match['date'])}前退出北约吗？"

    return None


def _translate_date(value: str) -> str:
    text = value.strip().rstrip("?")
    match = re.fullmatch(r"(?P<month>[A-Za-z]+) (?P<day>\d{1,2}), (?P<year>\d{4})", text)
    if match and match["month"] in MONTH_LABELS:
        return f"{match['year']}年{MONTH_LABELS[match['month']]}{match['day']}日"
    match = re.fullmatch(r"(?P<month>[A-Za-z]+) (?P<day>\d{1,2})", text)
    if match and match["month"] in MONTH_LABELS:
        return f"{MONTH_LABELS[match['month']]}{match['day']}日"
    match = re.fullmatch(r"(?P<month>[A-Za-z]+) (?P<year>\d{4})", text)
    if match and match["month"] in MONTH_LABELS:
        return f"{match['year']}年{MONTH_LABELS[match['month']]}"
    return _replace_terms(text)


def _entity_label(value: str) -> str:
    return ENTITY_LABELS.get(value, value)


def _polish_translated_title(value: str) -> str:
    translated = re.sub(r"\s+", " ", value).strip()
    translated = translated.replace("美国 announce", "美国宣布")
    translated = translated.replace("美国 enter a 衰退", "美国陷入衰退")
    translated = translated.replace("价格高于 $", "价格高于 ")
    translated = translated.replace("价格低于 $", "价格低于 ")
    translated = translated.replace("$", "")
    translated = translated.replace(" ,", "，")
    translated = translated.replace(" .", "。")
    translated = translated.replace(" 前", "前")
    translated = translated.replace(" 后", "后")
    return translated
