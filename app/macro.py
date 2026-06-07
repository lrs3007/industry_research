from __future__ import annotations

import json
import math
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_MACRO_CACHE_PATH = Path("data/macro_cache.json")


MACRO_GROUPS: tuple[dict[str, object], ...] = (
    {
        "key": "growth_demand",
        "label": "总量与需求",
        "description": "跟踪经济总量、工业生产、投资和居民消费的趋势强弱。",
        "indicators": (
            {
                "key": "gdp",
                "name": "GDP",
                "frequency": "季度",
                "source": "国家统计局",
                "watch": "实际 GDP 当季同比、两年复合、名义 GDP 与平减指数",
                "signal": "验证增长中枢和盈利周期位置",
                "related": "股指、长债、工业品",
            },
            {
                "key": "industry",
                "name": "工业",
                "frequency": "月度",
                "source": "国家统计局",
                "watch": "工业增加值、制造业增加值、产能利用率",
                "signal": "识别生产修复、库存周期和顺周期资产弹性",
                "related": "工业品、周期股、信用利差",
            },
            {
                "key": "investment",
                "name": "投资",
                "frequency": "月度",
                "source": "国家统计局",
                "watch": "固定资产投资、制造业投资、基建投资、民间投资",
                "signal": "观察政策托底和资本开支动能",
                "related": "建筑链、机械、有色、长债",
            },
            {
                "key": "consumption",
                "name": "消费",
                "frequency": "月度",
                "source": "国家统计局",
                "watch": "社零、服务零售、餐饮、汽车和地产后周期消费",
                "signal": "判断内需韧性和居民部门风险偏好",
                "related": "消费股、可选消费、人民币资产",
            },
        ),
    },
    {
        "key": "prices_sentiment",
        "label": "价格与景气",
        "description": "跟踪通胀、工业价格和采购经理景气对盈利与政策的约束。",
        "indicators": (
            {
                "key": "cpi",
                "name": "CPI",
                "frequency": "月度",
                "source": "国家统计局",
                "watch": "CPI 同比、核心 CPI、食品与服务分项",
                "signal": "衡量居民端通胀压力和货币政策空间",
                "related": "利率债、黄金、消费板块",
            },
            {
                "key": "ppi",
                "name": "PPI",
                "frequency": "月度",
                "source": "国家统计局",
                "watch": "PPI 同比、生产资料、采掘和原材料分项",
                "signal": "观察上游盈利、库存周期和工业通缩压力",
                "related": "有色、化工、钢铁、周期股",
            },
            {
                "key": "pmi",
                "name": "PMI",
                "frequency": "月度",
                "source": "国家统计局/财新",
                "watch": "制造业 PMI、新订单、生产、价格、服务业商务活动",
                "signal": "提前识别景气拐点和需求扩张/收缩",
                "related": "股指、工业品、人民币汇率",
            },
        ),
    },
    {
        "key": "credit_liquidity",
        "label": "金融信用",
        "description": "跟踪信用扩张、货币供给和银行信贷对资产定价的影响。",
        "indicators": (
            {
                "key": "tsf",
                "name": "社融",
                "frequency": "月度",
                "source": "人民银行",
                "watch": "新增社融、社融存量同比、政府债、企业债和表外融资",
                "signal": "判断宽信用进程和实体融资需求",
                "related": "A股、地产链、信用债",
            },
            {
                "key": "m2",
                "name": "M2",
                "frequency": "月度",
                "source": "人民银行",
                "watch": "M2 同比、M1 同比、M1-M2 剪刀差",
                "signal": "跟踪资金活化程度和企业现金流预期",
                "related": "股债跷跷板、银行、成长股",
            },
            {
                "key": "credit",
                "name": "信贷",
                "frequency": "月度",
                "source": "人民银行",
                "watch": "新增人民币贷款、居民中长贷、企业中长贷、票据融资",
                "signal": "拆分居民和企业融资意愿",
                "related": "银行、地产、消费、长债",
            },
        ),
    },
    {
        "key": "policy_property",
        "label": "财政与地产",
        "description": "跟踪财政支出强度和地产链景气，是内需和信用修复的关键验证项。",
        "indicators": (
            {
                "key": "fiscal",
                "name": "财政",
                "frequency": "月度",
                "source": "财政部",
                "watch": "公共财政收入支出、政府性基金、专项债发行和使用节奏",
                "signal": "观察稳增长力度和基建资金来源",
                "related": "基建链、城投债、长端利率",
            },
            {
                "key": "property",
                "name": "地产",
                "frequency": "月度",
                "source": "国家统计局/住建部",
                "watch": "销售面积、投资、新开工、竣工、房价和库存",
                "signal": "判断地产链拖累或修复斜率",
                "related": "地产链、银行、黑色商品",
            },
        ),
    },
    {
        "key": "external_markets",
        "label": "外需与市场价格",
        "description": "跟踪外需、汇率、利率和跨资产价格对宏观预期的实时反馈。",
        "indicators": (
            {
                "key": "trade",
                "name": "进出口",
                "frequency": "月度",
                "source": "海关总署",
                "watch": "出口、进口、贸易差额、重点区域和商品分项",
                "signal": "观察外需景气和产业链竞争力",
                "related": "出口链、人民币、航运",
            },
            {
                "key": "fx",
                "name": "汇率",
                "frequency": "日度",
                "source": "外汇交易中心",
                "watch": "人民币中间价、即期汇率、CFETS 指数、美元指数",
                "signal": "反映外部压力、资本流动和风险偏好",
                "related": "人民币资产、黄金、出口股",
            },
            {
                "key": "rates",
                "name": "利率",
                "frequency": "日度",
                "source": "人民银行/交易市场",
                "watch": "DR007、国债收益率曲线、MLF/LPR、同业存单利率",
                "signal": "判断流动性松紧和债券定价锚",
                "related": "利率债、银行、成长股",
            },
            {
                "key": "asset_prices",
                "name": "股债商品价格",
                "frequency": "日度",
                "source": "交易所/行情数据",
                "watch": "股指、国债期货、信用利差、南华商品、黄金、原油和铜",
                "signal": "用市场价格验证宏观叙事是否被定价",
                "related": "股票、债券、商品、汇率",
            },
        ),
    },
    {
        "key": "high_frequency",
        "label": "高频跟踪",
        "description": "用周度/日度数据提前验证月度宏观数据方向。",
        "indicators": (
            {
                "key": "high_frequency_production",
                "name": "高频生产",
                "frequency": "日度/周度",
                "source": "行业高频数据",
                "watch": "高炉开工、焦化开工、PTA、轮胎开工、发电耗煤、货运物流",
                "signal": "提前跟踪工业生产和开工强度",
                "related": "黑色、有色、化工、工业股",
            },
            {
                "key": "property_sales",
                "name": "地产销售数据",
                "frequency": "日度/周度",
                "source": "城市成交/行业高频数据",
                "watch": "30城商品房成交、二手房成交、土地成交和库存去化",
                "signal": "高频确认地产销售修复能否传导到投资和信用",
                "related": "地产链、银行、黑色商品",
            },
        ),
    },
)


INDICATOR_CONNECTORS: dict[str, dict[str, object]] = {
    "gdp": {
        "kind": "ak",
        "api": "macro_china_gdp_yearly",
        "period": ("日期",),
        "value": ("今值",),
        "valueLabel": "GDP年率",
        "unit": "%",
    },
    "industry": {
        "kind": "ak",
        "api": "macro_china_gyzjz",
        "period": ("月份",),
        "release": ("发布时间",),
        "value": ("同比增长",),
        "change": ("累计增长",),
        "valueLabel": "工业增加值同比",
        "changeLabel": "累计增长",
        "unit": "%",
    },
    "investment": {
        "kind": "ak",
        "api": "macro_china_gdzctz",
        "period": ("月份",),
        "value": ("同比增长",),
        "change": ("环比增长",),
        "valueLabel": "固定资产投资同比",
        "changeLabel": "环比增长",
        "unit": "%",
    },
    "consumption": {
        "kind": "ak",
        "api": "macro_china_consumer_goods_retail",
        "period": ("月份",),
        "value": ("同比增长",),
        "change": ("环比增长",),
        "valueLabel": "社零同比",
        "changeLabel": "环比增长",
        "unit": "%",
    },
    "cpi": {
        "kind": "ak",
        "api": "macro_china_cpi",
        "period": ("月份",),
        "value": ("全国-同比增长",),
        "change": ("全国-环比增长",),
        "valueLabel": "全国CPI同比",
        "changeLabel": "全国CPI环比",
        "unit": "%",
    },
    "ppi": {
        "kind": "ak",
        "api": "macro_china_ppi",
        "period": ("月份",),
        "value": ("当月同比增长",),
        "change": ("当月",),
        "valueLabel": "PPI同比",
        "changeLabel": "PPI指数",
        "unit": "%",
    },
    "pmi": {
        "kind": "ak",
        "api": "macro_china_pmi",
        "period": ("月份",),
        "value": ("制造业-指数",),
        "change": ("非制造业-指数",),
        "valueLabel": "制造业PMI",
        "changeLabel": "非制造业PMI",
        "unit": "点",
    },
    "tsf": {
        "kind": "ak",
        "api": "macro_china_shrzgm",
        "period": ("月份", "统计时间", "日期"),
        "value": ("当月", "社会融资规模增量", "新增社会融资规模"),
        "valueLabel": "社融增量",
        "unit": "亿元",
    },
    "m2": {
        "kind": "ak",
        "api": "macro_china_supply_of_money",
        "period": ("统计时间",),
        "value": ("货币和准货币（广义货币M2）同比增长",),
        "change": ("货币(狭义货币M1)同比增长",),
        "valueLabel": "M2同比",
        "changeLabel": "M1同比",
        "unit": "%",
    },
    "credit": {
        "kind": "ak",
        "api": "macro_china_new_financial_credit",
        "period": ("月份",),
        "value": ("当月",),
        "change": ("当月-同比增长",),
        "valueLabel": "新增人民币贷款",
        "changeLabel": "贷款同比",
        "unit": "亿元",
    },
    "fiscal": {
        "kind": "ak",
        "api": "macro_china_czsr",
        "period": ("月份",),
        "value": ("累计-同比增长",),
        "change": ("当月-同比增长",),
        "valueLabel": "财政收入累计同比",
        "changeLabel": "财政收入当月同比",
        "unit": "%",
    },
    "property": {
        "kind": "ak",
        "api": "macro_china_real_estate",
        "period": ("日期",),
        "value": ("最新值",),
        "change": ("近1年涨跌幅",),
        "valueLabel": "国房景气指数",
        "changeLabel": "近1年涨跌幅",
        "unit": "点",
    },
    "trade": {
        "kind": "ak",
        "api": "macro_china_hgjck",
        "period": ("月份",),
        "value": ("当月出口额-同比增长",),
        "change": ("当月进口额-同比增长",),
        "valueLabel": "出口同比",
        "changeLabel": "进口同比",
        "unit": "%",
    },
    "fx": {
        "kind": "ak",
        "api": "currency_boc_safe",
        "period": ("日期",),
        "value": ("美元",),
        "valueLabel": "美元兑人民币",
        "scale": 0.01,
        "note": "接口返回人民币/100美元，展示时折算为美元兑人民币。",
        "unit": "",
    },
    "rates": {
        "kind": "ak",
        "api": "macro_china_lpr",
        "period": ("TRADE_DATE",),
        "value": ("LPR1Y",),
        "change": ("LPR5Y",),
        "valueLabel": "1年期LPR",
        "changeLabel": "5年期以上LPR",
        "unit": "%",
    },
    "asset_prices": {
        "kind": "composite_asset_prices",
    },
    "high_frequency_production": {
        "kind": "ak",
        "api": "macro_china_daily_energy",
        "period": ("日期",),
        "value": ("日耗",),
        "change": ("沿海六大电库存",),
        "valueLabel": "六大发电集团日耗",
        "changeLabel": "沿海六大电库存",
        "unit": "万吨",
    },
    "property_sales": {
        "kind": "ak",
        "api": "macro_china_real_estate",
        "period": ("日期",),
        "value": ("近1年涨跌幅",),
        "change": ("最新值",),
        "valueLabel": "地产景气近1年涨跌幅",
        "changeLabel": "国房景气指数",
        "unit": "%",
        "status": "已接入替代",
        "note": "免费高频城市成交源分散；当前先用国房景气指数近1年涨跌幅代理，后续可接地方房管城市成交爬虫。",
    },
}


def macro_dashboard_payload(cache_path: Path = DEFAULT_MACRO_CACHE_PATH, refresh: bool = False) -> dict[str, object]:
    cache = _load_macro_cache(cache_path)
    if refresh:
        refreshed = refresh_macro_dashboard(cache_path)
        if refreshed["observations"]:
            cache = refreshed

    observations = cache.get("observations", {}) if isinstance(cache, dict) else {}
    groups = [_group_to_dict(group, observations) for group in MACRO_GROUPS]
    indicator_count = sum(len(group["indicators"]) for group in groups)
    connected_count = sum(
        1
        for group in groups
        for indicator in group["indicators"]
        if str(indicator.get("status", "")).startswith("已接入")
    )
    fetched_at = cache.get("fetchedAt", "") if isinstance(cache, dict) else ""
    return {
        "mode": "免费数据接入",
        "status": "已接入免费源" if connected_count else "待刷新宏观数据",
        "fetchedAt": fetched_at,
        "summary": {
            "groupCount": len(groups),
            "indicatorCount": indicator_count,
            "connectedCount": connected_count,
            "frequencyMix": ["季度", "月度", "日度/周度"],
        },
        "groups": groups,
    }


def refresh_macro_dashboard(cache_path: Path = DEFAULT_MACRO_CACHE_PATH) -> dict[str, object]:
    observations = {key: _collect_indicator(key, connector) for key, connector in INDICATOR_CONNECTORS.items()}
    payload = {
        "fetchedAt": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "observations": observations,
    }
    _save_macro_cache(cache_path, payload)
    return payload


def _group_to_dict(group: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
    return {
        "key": group["key"],
        "label": group["label"],
        "description": group["description"],
        "indicators": [_indicator_to_dict(indicator, observations) for indicator in group["indicators"]],
    }


def _indicator_to_dict(indicator: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
    key = str(indicator["key"])
    observation = observations.get(key)
    connector = INDICATOR_CONNECTORS.get(key, {})
    item = {
        **indicator,
        "sourceApi": connector.get("api", connector.get("kind", "manual")),
        "status": "待刷新",
    }
    if isinstance(observation, dict):
        item.update(observation)
    return item


def _collect_indicator(key: str, connector: dict[str, object]) -> dict[str, object]:
    try:
        if connector.get("kind") == "ak":
            return _collect_ak_indicator(connector)
        if connector.get("kind") == "composite_asset_prices":
            return _collect_asset_prices()
        return {"status": "待接入", "error": "未配置数据连接器"}
    except Exception as exc:  # noqa: BLE001 - data sources fail independently
        return {
            "status": "采集失败",
            "error": _short_error(exc),
            "sourceApi": connector.get("api", key),
        }


def _collect_ak_indicator(connector: dict[str, object]) -> dict[str, object]:
    ak = _akshare()
    api = str(connector["api"])
    params = connector.get("params", {})
    df = getattr(ak, api)(**params)
    row, period_column = _latest_row(df, connector.get("period", ()))
    value_column = _pick_column(row.index, connector.get("value", ()))
    change_column = _pick_column(row.index, connector.get("change", ()), required=False)
    release_column = _pick_column(row.index, connector.get("release", ()), required=False)

    value = _scaled_value(row[value_column], connector.get("scale"))
    unit = str(connector.get("unit", ""))
    current = {
        "period": _string_value(row[period_column]) if period_column else "",
        "value": value,
        "unit": unit,
        "valueText": _value_text(value, unit),
        "valueLabel": str(connector.get("valueLabel", value_column)),
        "sourceApi": api,
        "rawColumns": [str(column) for column in df.columns],
        "latestRow": {str(column): _json_value(row[column]) for column in row.index},
    }
    if change_column:
        change_value = _json_value(row[change_column])
        current["change"] = change_value
        current["changeText"] = _value_text(change_value, unit if "增长" in change_column or "涨跌幅" in change_column else "")
        current["changeLabel"] = str(connector.get("changeLabel", change_column))
    if release_column:
        current["releaseDate"] = _string_value(row[release_column])
    note = connector.get("note")
    if note:
        current["note"] = note

    return {
        "status": _status_for_current(current, str(connector.get("status", "已接入"))),
        "current": current,
    }


def _collect_asset_prices() -> dict[str, object]:
    parts: list[dict[str, object]] = []
    errors: list[str] = []
    try:
        parts.append(_stock_index_part())
    except Exception as exc:  # noqa: BLE001
        errors.append(f"沪深300: {_short_error(exc)}")
    try:
        parts.append(_bond_yield_part())
    except Exception as exc:  # noqa: BLE001
        errors.append(f"10年国债: {_short_error(exc)}")
    try:
        parts.append(_commodity_part())
    except Exception as exc:  # noqa: BLE001
        errors.append(f"商品指数: {_short_error(exc)}")

    parts = [part for part in parts if part]
    if not parts:
        return {"status": "采集失败", "error": "；".join(errors), "sourceApi": "composite_asset_prices"}

    return {
        "status": "已接入" if not errors else "部分接入",
        "current": {
            "period": " / ".join(part["period"] for part in parts if part.get("period")),
            "value": " / ".join(part["valueText"] for part in parts),
            "unit": "",
            "valueText": " / ".join(part["valueText"] for part in parts),
            "valueLabel": "沪深300收盘 / 10年国债收益率 / 商品价格指数",
            "sourceApi": "stock_zh_index_daily + bond_china_yield + macro_china_commodity_price_index",
            "parts": parts,
            "note": "组合指标，任一上游失败时保留其余可用数据。",
            "errors": errors,
        },
    }


def _stock_index_part() -> dict[str, object]:
    ak = _akshare()
    df = ak.stock_zh_index_daily(symbol="sh000300")
    row, period_column = _latest_row(df, ("date",))
    value = _json_value(row["close"])
    return {
        "name": "沪深300",
        "period": _string_value(row[period_column]),
        "value": value,
        "valueText": f"沪深300 {_value_text(value, '')}",
        "sourceApi": "stock_zh_index_daily",
    }


def _bond_yield_part() -> dict[str, object]:
    ak = _akshare()
    end = datetime.now().date()
    start = end - timedelta(days=20)
    df = ak.bond_china_yield(start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"))
    df = df[df["曲线名称"].astype(str) == "中债国债收益率曲线"]
    row, period_column = _latest_row(df, ("日期",))
    value = _json_value(row["10年"])
    return {
        "name": "10年国债",
        "period": _string_value(row[period_column]),
        "value": value,
        "valueText": f"10年国债 {_value_text(value, '%')}",
        "sourceApi": "bond_china_yield",
    }


def _commodity_part() -> dict[str, object]:
    ak = _akshare()
    df = ak.macro_china_commodity_price_index()
    row, period_column = _latest_row(df, ("日期",))
    value = _json_value(row["最新值"])
    return {
        "name": "商品价格指数",
        "period": _string_value(row[period_column]),
        "value": value,
        "valueText": f"商品指数 {_value_text(value, '点')}",
        "sourceApi": "macro_china_commodity_price_index",
    }


def _latest_row(df: Any, period_candidates: object) -> tuple[Any, str | None]:
    if df is None or getattr(df, "empty", True):
        raise ValueError("数据源返回空表")
    period_column = _pick_column(df.columns, period_candidates, required=False)
    clean_df = df.dropna(how="all").copy()
    if clean_df.empty:
        raise ValueError("数据源返回空表")
    if period_column:
        clean_df["_period_sort"] = clean_df[period_column].map(_parse_period_sort)
        clean_df = clean_df.sort_values("_period_sort", kind="mergesort")
        clean_df = clean_df.drop(columns=["_period_sort"])
    return clean_df.iloc[-1], period_column


def _pick_column(columns: object, candidates: object, required: bool = True) -> str | None:
    column_list = [str(column) for column in columns]
    for candidate in candidates or ():
        if str(candidate) in column_list:
            return str(candidate)
    for candidate in candidates or ():
        matches = [column for column in column_list if str(candidate) in column]
        if matches:
            return matches[0]
    if required:
        raise KeyError(f"未找到字段: {', '.join(str(item) for item in candidates or ())}")
    return None


def _parse_period_sort(value: object) -> datetime:
    text = _string_value(value)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    match = re.search(r"(\d{4})年(\d{1,2})月", text)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), 1)
    match = re.search(r"(\d{4})[.年/-](\d{1,2})", text)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), 1)
    match = re.search(r"(\d{4})", text)
    if match:
        return datetime(int(match.group(1)), 1, 1)
    return datetime.min


def _value_text(value: object, unit: str) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return "--"
        formatted = f"{float(value):,.2f}".rstrip("0").rstrip(".")
        return f"{formatted}{unit}"
    if value in (None, ""):
        return "--"
    return f"{value}{unit}"


def _scaled_value(value: object, scale: object) -> object:
    value = _json_value(value)
    if scale is None or value in (None, ""):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) * float(scale)
    return value


def _status_for_current(current: dict[str, object], default: str) -> str:
    period = current.get("period")
    parsed = _parse_period_sort(period)
    if parsed != datetime.min and datetime.now() - parsed > timedelta(days=370):
        return "已接入（数据偏旧）"
    return default


def _json_value(value: object) -> object:
    if value is None:
        return None
    if type(value).__name__ in {"NAType", "NaTType"}:
        return None
    if hasattr(value, "item"):
        value = value.item()
    try:
        if value != value:
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _string_value(value: object) -> str:
    value = _json_value(value)
    return "" if value is None else str(value)


def _short_error(exc: Exception) -> str:
    return re.sub(r"\s+", " ", str(exc)).strip()[:220] or type(exc).__name__


def _akshare() -> Any:
    try:
        import akshare as ak  # type: ignore
    except ImportError as exc:
        raise RuntimeError("当前 Python 环境未安装 akshare，请先执行 pip install -U akshare") from exc
    return ak


def _load_macro_cache(cache_path: Path) -> dict[str, object]:
    if not cache_path.is_file():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_macro_cache(cache_path: Path, payload: dict[str, object]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
