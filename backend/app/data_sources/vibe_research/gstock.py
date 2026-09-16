"""Adapted data source from local Vibe-Research.

Consumer Alpha Radar uses this as an objective market-data input layer;
product-specific discovery logic remains in app.skills/app.agents.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from app.data_sources.vibe_research import astock

_UA_H = {"User-Agent": astock.UA}
_GS_HOSTS = ("push2.eastmoney.com", "push2delay.eastmoney.com")
_gs_host = [0]  # 当前可用主机下标；首次 push2 掉连后 latch 到 push2delay

# 全球指数（东财 push2 secid）—— A 股看隔夜外围脸色的核心几个，均已实测。
_INDICES = (
    {"key": "dji", "name": "道琼斯", "secid": "100.DJIA", "region": "美股"},
    {"key": "spx", "name": "标普500", "secid": "100.SPX", "region": "美股"},
    {"key": "ndx", "name": "纳斯达克", "secid": "100.NDX", "region": "美股"},
    {"key": "hsi", "name": "恒生指数", "secid": "100.HSI", "region": "港股"},
    {"key": "hstech", "name": "恒生科技", "secid": "124.HSTECH", "region": "港股"},
)

# 搜索返回的 MktNum → (secucode 后缀, 市场名)
_MKT = {105: (".O", "NASDAQ"), 106: (".N", "NYSE"), 107: (".O", "US"), 116: (".HK", "HK"),
        177: (".KS", "KR")}  # 177=韩股（Kospi/Kosdaq，含三星/SK海力士等半导体龙头）；东财仅行情、无 F10 财务

# Eastmoney push2 fields: f162=PE(TTM), f164=PB, f167=turnover (%),
# f116=market cap. Keep these in the same live quote request as price data.
_QUOTE_FIELDS = "f43,f44,f45,f46,f48,f57,f58,f59,f60,f116,f162,f164,f167,f170"


def _push2_stock_get(secid: str, fields: str) -> dict | None:
    """东财 push2 stock/get：push2 优先、失败降级 push2delay；latch 可用主机。空数据返回 None。"""
    params = {"secid": secid, "fields": fields}
    for i in range(_gs_host[0], len(_GS_HOSTS)):
        try:
            r = astock.em_get(f"https://{_GS_HOSTS[i]}/api/qt/stock/get",
                              params=params, headers=_UA_H, timeout=10)
            d = r.json().get("data")
        except Exception:
            continue
        if d:
            _gs_host[0] = i
            return d
    return None


def _price(d: dict, key: str):
    """f43 等价格字段：除以 10^f59 还原。'-' / None → None。"""
    v = d.get(key)
    if not isinstance(v, (int, float)):
        return None
    dec = d.get("f59")
    if not isinstance(dec, int):  # 注意：不能用 `or 2`——韩元等 f59=0 会被误判成 2，价格被多除 100 倍
        dec = 2
    return round(v / (10 ** dec), dec)


def _quote_from(d: dict) -> dict:
    chg = d.get("f170")
    return {
        "code": d.get("f57"), "name": d.get("f58"),
        "price": _price(d, "f43"), "open": _price(d, "f46"),
        "high": _price(d, "f44"), "low": _price(d, "f45"),
        "prev_close": _price(d, "f60"),
        "amount": d.get("f48") if isinstance(d.get("f48"), (int, float)) else None,
        "mcap": d.get("f116") if isinstance(d.get("f116"), (int, float)) and d.get("f116") else None,
        "pe_ttm": d.get("f162") if isinstance(d.get("f162"), (int, float)) else None,
        "pb": d.get("f164") if isinstance(d.get("f164"), (int, float)) else None,
        "turnover_pct": d.get("f167") if isinstance(d.get("f167"), (int, float)) else None,
        "change_pct": round(chg / 100, 2) if isinstance(chg, (int, float)) else None,
    }


def global_indices() -> list[dict]:
    """全球指数快照（道指 / 标普500 / 纳斯达克 / 恒生 / 恒生科技）。源无的档跳过。"""
    out = []
    for idx in _INDICES:
        d = _push2_stock_get(idx["secid"], "f43,f57,f58,f59,f60,f170")
        if not d:
            continue
        chg = d.get("f170")
        out.append({
            "key": idx["key"], "name": idx["name"], "region": idx["region"],
            "price": _price(d, "f43"),
            "change_pct": round(chg / 100, 2) if isinstance(chg, (int, float)) else None,
        })
    return out


def _search(q: str) -> dict | None:
    """东财搜索一次：市场过滤 + **精确代码匹配优先**，退而取第一条。

    只按 MktNum 过滤挑不出正股——东财搜 AAPL 会混入 AAPL22(票据)/AAPB(2倍做多ETF)，
    搜 BABA 混入 05593(窝轮)，且 SecurityType 分不开(正股与 ETF 同为 Type7、正股港股与窝轮同为 Type6)。
    正股的 Code 恰好等于查询词，故精确匹配 Code==q 最稳；无精确匹配(名称查询)才退回第一条。
    """
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {"input": q, "type": 14,
              "token": "D43BF722C8E33BDC906FB84D85E326E8", "count": 10}
    try:
        r = astock.em_get(url, params=params, headers=_UA_H, timeout=10)
        rows = (r.json().get("QuotationCodeTable") or {}).get("Data") or []
    except Exception:
        return None
    matches = []
    for s in rows:
        try:
            mkt = int(s.get("MktNum"))
        except (TypeError, ValueError):
            continue
        if mkt in _MKT:
            matches.append((mkt, s))
    if not matches:
        return None
    mkt, s = next(((m, x) for m, x in matches if str(x.get("Code", "")).upper() == q), matches[0])
    suffix, market = _MKT[mkt]
    code = s.get("Code", "")
    return {"code": code, "name": s.get("Name", ""), "secid_prefix": mkt,
            "secucode": f"{code}{suffix}", "market": market}


def resolve_symbol(query: str) -> dict | None:
    """代码/名称 → {code, name, secid_prefix, secucode, market}。认美股/港股/韩股。
    数字型港股短代码（如 `700`）补零到 5 位再试一次（东财按 `00700` 收）。
    韩股用国际后缀 `.KS`/`.KQ`/`.KR`（如三星 `005930.KS`）——韩股代码与 A 股同为 6 位数字，
    需显式后缀区分，否则前端会按 A 股处理、后端也搜不到韩股。"""
    q = query.strip().upper()
    if not q:
        return None
    for suf in (".HK", ".US", ".KS", ".KQ", ".KR"):  # 按裸代码搜索，市场由后缀/东财结果确定
        if q.endswith(suf):
            q = q[: -len(suf)]
            break
    # Numeric HKEX codes are unambiguous. Eastmoney's search endpoint can
    # intermittently omit valid HK listings, so do not make detail pages
    # depend on that search call.
    if q.isdigit() and 4 <= len(q) <= 5:
        code = q.zfill(4)
        return {
            "code": code,
            "name": "",
            "secid_prefix": 116,
            "secucode": f"{code}.HK",
            "market": "HK",
        }
    hit = _search(q)
    if hit is None and q.isdigit() and len(q) < 5:
        hit = _search(q.zfill(5))
    return hit


def _key_metrics(secucode: str) -> dict | None:
    """东财 GMAININDICATOR 最新一期关键财务指标（美股/港股中文字段）。"""
    market = "HK" if secucode.endswith(".HK") else "US"
    rows = astock.eastmoney_datacenter(
        f"RPT_{market}F10_FN_GMAININDICATOR",
        filter_str=f'(SECUCODE="{secucode}")',
        page_size=1, sort_columns="REPORT_DATE", sort_types="-1")
    if not rows:
        return None
    m = rows[0]
    return {
        "report_date": str(m.get("REPORT_DATE") or "")[:10],
        "revenue": m.get("OPERATE_INCOME"),
        "revenue_yoy": m.get("OPERATE_INCOME_YOY"),
        "net_profit": m.get("PARENT_HOLDER_NETPROFIT") or m.get("HOLDER_PROFIT"),
        "eps": m.get("BASIC_EPS"),
        "roe": m.get("ROE_AVG"),
        "gross_margin": m.get("GROSS_PROFIT_RATIO"),
        "net_margin": m.get("NET_PROFIT_RATIO"),
        "debt_ratio": m.get("DEBT_ASSET_RATIO"),
    }


def us_hk_stock(query: str) -> dict:
    """个股聚合（美/港）：解析代码 → 行情 + 关键财务指标。查不到返回 {}。"""
    info = resolve_symbol(query)
    if not info:
        return {}
    yahoo = _yahoo_chart(query)
    if yahoo:
        quote = _quote_from_yahoo(yahoo)
        # Fill Yahoo's commonly missing turnover/amount fields from Eastmoney
        # when available, while keeping Yahoo as the reliable price source.
        d = _push2_stock_get(f"{info['secid_prefix']}.{info['code']}", _QUOTE_FIELDS)
        fallback = _quote_from(d or {})
        for key, value in fallback.items():
            if quote.get(key) is None and value is not None:
                quote[key] = value
    else:
        d = _push2_stock_get(f"{info['secid_prefix']}.{info['code']}", _QUOTE_FIELDS)
        quote = _quote_from(d or {})
    return {
        "code": info["code"],
        "name": info["name"] or quote.get("name") or info["code"],
        "market": info["market"],
        "quote": quote,
        "metrics": _key_metrics(info["secucode"]) if info["market"] != "KR" else None,  # 韩股东财无 F10 财务
    }


def company_news(query: str, limit: int = 10) -> list[dict]:
    """Company news from Yahoo Finance's public search endpoint.

    Yahoo's chart endpoint is already the primary global quote fallback in this
    module.  Its search endpoint also returns recent company-linked stories for
    US/HK/KR symbols without requiring an additional API key.  Keep the raw
    provider details out of the analysis layer by normalising them here.
    """
    import requests

    symbol = _yahoo_symbol(query)
    if not symbol:
        return []
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={quote(symbol)}"
    params = {
        "quotesCount": 1,
        "newsCount": max(1, min(int(limit), 20)),
        "enableFuzzyQuery": "false",
    }
    try:
        payload = requests.get(url, params=params, headers=_UA_H, timeout=10).json()
    except Exception:
        return []

    rows = []
    for item in payload.get("news") or []:
        title = str(item.get("title") or "").strip()
        link = item.get("link") or item.get("url")
        if not title or not link:
            continue
        published = item.get("providerPublishTime")
        try:
            published_at = datetime.fromtimestamp(int(published)).isoformat()
        except (TypeError, ValueError, OSError):
            published_at = None
        rows.append(
            {
                "title": title,
                "source": item.get("publisher") or "Yahoo Finance",
                "url": link,
                "published_at": published_at,
                "summary": item.get("summary") or "",
                "provider": "yahoo",
            }
        )
    return rows[:limit]


def us_hk_quote(query: str) -> dict:
    """美/港快照：首屏优先 Yahoo chart，失败再退东财。"""
    yahoo = _yahoo_chart(query)
    if yahoo:
        quote = _quote_from_yahoo(yahoo)
        # Yahoo's chart metadata omits turnover and traded amount for many
        # HK listings. Fill only missing fields from Eastmoney's live quote.
        info = resolve_symbol(query)
        if info:
            fallback = _quote_from(_push2_stock_get(f"{info['secid_prefix']}.{info['code']}", _QUOTE_FIELDS) or {})
            for key, value in fallback.items():
                if quote.get(key) is None and value is not None:
                    quote[key] = value
        return {
            "code": _display_code_from_yahoo(query),
            "name": yahoo.get("name"),
            "market": yahoo.get("market"),
            "quote": quote,
        }

    info = resolve_symbol(query)
    if not info:
        return {}
    d = _push2_stock_get(f"{info['secid_prefix']}.{info['code']}", _QUOTE_FIELDS)
    quote = _quote_from(d or {})
    return {
        "code": info["code"],
        "name": info["name"] or quote.get("name") or info["code"],
        "market": info["market"],
        "quote": quote,
    }


def us_hk_kline(query: str, category: int = 4, offset: int = 90) -> dict:
    """美/港 K 线：首屏优先 Yahoo chart，失败再退东财。"""
    yahoo = _yahoo_chart(query)
    if yahoo:
        rows = _kline_from_yahoo(yahoo, offset=offset)
        if rows:
            return {
                "code": _display_code_from_yahoo(query),
                "name": yahoo.get("name"),
                "market": yahoo.get("market"),
                "daily_kline": rows,
            }

    info = resolve_symbol(query)
    if not info:
        return {"daily_kline": []}
    klt = {4: "101", 5: "102", 6: "103", 11: "60"}.get(category, "101")
    params = {
        "secid": f"{info['secid_prefix']}.{info['code']}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": klt,
        "fqt": "1",
        "end": "20500101",
        "lmt": str(offset),
    }
    headers = {"User-Agent": astock.UA, "Referer": "https://quote.eastmoney.com/"}
    try:
        data = astock.em_get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params=params,
            headers=headers,
            timeout=15,
        ).json().get("data") or {}
    except Exception:
        data = {}

    rows = []
    for line in data.get("klines") or []:
        p = line.split(",")
        if len(p) < 11:
            continue

        def _f(value):
            try:
                return float(value) if value not in ("", "-") else None
            except ValueError:
                return None

        rows.append(
            {
                "date": p[0],
                "open": _f(p[1]),
                "close": _f(p[2]),
                "high": _f(p[3]),
                "low": _f(p[4]),
                "volume": _f(p[5]),
                "amount": _f(p[6]),
                "amplitude_pct": _f(p[7]),
                "change_pct": _f(p[8]),
                "change_amt": _f(p[9]),
                "turnover_pct": _f(p[10]),
            }
        )
    return {
        "code": info["code"],
        "name": info["name"],
        "market": info["market"],
        "daily_kline": rows,
    }


def _yahoo_symbol(query: str) -> str:
    q = query.strip().upper()
    if q.endswith(".US"):
        return q[:-3]
    if q.endswith(".HK"):
        base = q[:-3]
        # Yahoo Finance expects HKEX's four-digit code (e.g. 0220.HK,
        # 0700.HK). Stripping leading zeroes turns valid symbols into
        # non-existent tickers such as 220.HK.
        return f"{base.zfill(4)}.HK"
    if q.isdigit() and 4 <= len(q) <= 5:
        return f"{q.zfill(4)}.HK"
    return q


def _display_code_from_yahoo(query: str) -> str:
    q = query.strip().upper()
    if q.endswith(".HK"):
        return q[:-3].zfill(5)
    if q.isdigit() and 4 <= len(q) <= 5:
        return q.zfill(5)
    if q.endswith(".US"):
        return q[:-3]
    return q


def _market_from_yahoo_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        return "HK"
    return "US"


def _yahoo_chart(query: str) -> dict | None:
    """Yahoo chart returns quote metadata and historical rows in one quick call."""
    import requests

    symbol = _yahoo_symbol(query)
    if not symbol:
        return None
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "6mo", "interval": "1d", "events": "history"}
    headers = {"User-Agent": astock.UA}
    try:
        chart = requests.get(url, params=params, headers=headers, timeout=10).json().get("chart") or {}
    except Exception:
        return None
    result = (chart.get("result") or [None])[0] or {}
    if not result:
        return None
    meta = result.get("meta") or {}
    return {
        "symbol": symbol,
        "name": meta.get("longName") or meta.get("shortName") or meta.get("symbol"),
        "market": _market_from_yahoo_symbol(symbol),
        "meta": meta,
        "result": result,
    }


def _quote_from_yahoo(chart: dict) -> dict:
    meta = chart.get("meta") or {}
    price = meta.get("regularMarketPrice")
    prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    change_pct = None
    if isinstance(price, (int, float)) and isinstance(prev_close, (int, float)) and prev_close:
        change_pct = round((price - prev_close) / prev_close * 100, 2)
    volume = meta.get("regularMarketVolume") if isinstance(meta.get("regularMarketVolume"), (int, float)) else None
    # Yahoo does not expose turnover for every HK listing. A notional traded
    # amount can still be derived from the live price and volume.
    amount = price * volume if isinstance(price, (int, float)) and isinstance(volume, (int, float)) else None
    return {
        "code": meta.get("symbol"),
        "price": price if isinstance(price, (int, float)) else None,
        "open": meta.get("regularMarketOpen") if isinstance(meta.get("regularMarketOpen"), (int, float)) else None,
        "high": meta.get("regularMarketDayHigh") if isinstance(meta.get("regularMarketDayHigh"), (int, float)) else None,
        "low": meta.get("regularMarketDayLow") if isinstance(meta.get("regularMarketDayLow"), (int, float)) else None,
        "prev_close": prev_close if isinstance(prev_close, (int, float)) else None,
        "volume": volume,
        "amount": amount,
        "mcap": meta.get("marketCap") if isinstance(meta.get("marketCap"), (int, float)) else None,
        "pe_ttm": meta.get("trailingPE") if isinstance(meta.get("trailingPE"), (int, float)) else None,
        "pb": meta.get("priceToBook") if isinstance(meta.get("priceToBook"), (int, float)) else None,
        "turnover_pct": None,
        "change_pct": change_pct,
        "currency": meta.get("currency"),
        "source": "yahoo",
    }


def _kline_from_yahoo(chart: dict, offset: int = 90) -> list[dict]:
    result = chart.get("result") or {}
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
    rows = []
    for index, ts in enumerate(timestamps):
        try:
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            continue

        def _at(key: str):
            values = quote.get(key) or []
            value = values[index] if index < len(values) else None
            return round(value, 4) if isinstance(value, (int, float)) else None

        close = _at("close")
        if close is None:
            continue
        rows.append(
            {
                "date": date,
                "open": _at("open"),
                "close": close,
                "high": _at("high"),
                "low": _at("low"),
                "volume": _at("volume"),
                "amount": None,
                "source": "yahoo",
            }
        )
    return rows[-offset:]
