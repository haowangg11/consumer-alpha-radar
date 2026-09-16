import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.data_sources.vibe_research import astock, gstock, market, newsradar
from app.skills.base import Skill
from app.skills.errors import SkillInvalidPayloadError
from app.skills.metadata import SkillMetadata
from app.skills.responses import success_response


class MarketDataSkill(Skill):
    """
    Cross-market public data skill adapted from Vibe-Research.

    It returns objective market facts only: quotes, filings/news/industry
    signals, market breadth, and global stock snapshots. Discovery agents
    are responsible for turning these facts into opportunity hypotheses.
    """

    _CACHE: dict[str, tuple[float, dict]] = {}
    _QUOTE_TTL = 15
    _KLINE_TTL = 300
    _DETAIL_TTL = 120

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="market_data",
            description=(
                "Retrieves A-share, US/HK/KR, market overview, industry report, "
                "and sector-news signals from public sources."
            ),
            version="0.1.0",
            input_schema={
                "query_type": [
                    "a_share_quote",
                    "a_share_snapshot",
                    "a_share_detail",
                    "a_share_kline",
                    "global_stock_quote",
                    "global_stock_kline",
                    "global_stock",
                    "company_evidence",
                    "market_overview",
                    "news_radar",
                    "industry_reports",
                ]
            },
            output_schema={"data": "dict"},
            tags=["market-data", "a-share", "us-stock", "hk-stock", "news", "discovery"],
        )

    def run(self, query_type: str, payload: dict) -> dict:
        handlers = {
            "a_share_quote": self._a_share_quote,
            "a_share_snapshot": self._a_share_snapshot,
            "a_share_detail": self._a_share_detail,
            "a_share_kline": self._a_share_kline,
            "global_stock_quote": self._global_stock_quote,
            "global_stock_kline": self._global_stock_kline,
            "global_stock": self._global_stock,
            "company_evidence": self._company_evidence,
            "market_overview": self._market_overview,
            "news_radar": self._news_radar,
            "industry_reports": self._industry_reports,
        }
        if query_type not in handlers:
            raise SkillInvalidPayloadError(
                f"Market data skill does not support query_type '{query_type}'"
            )
        return success_response(skill="market_data", data=self._cached(query_type, payload or {}, handlers[query_type]))

    def _a_share_quote(self, payload: dict) -> dict:
        codes = payload.get("codes")
        if not isinstance(codes, list) or not codes:
            raise SkillInvalidPayloadError("a_share_quote requires non-empty 'codes' list")
        return astock.tencent_quote([str(code).strip() for code in codes])

    def _a_share_snapshot(self, payload: dict) -> dict:
        code = self._required_str(payload, "code")
        data = {
            "code": code,
            "quote": astock.tencent_quote([code]).get(code),
        }
        optional_calls = {
            "valuation": lambda: astock.full_valuation(code),
            "valuation_percentile": lambda: astock.valuation_percentile(code),
            "financials": lambda: astock.financials(code),
            "announcements": lambda: astock.announcements(code),
            "reports": lambda: astock.eastmoney_reports(code, max_pages=1)[:10],
            "fund_flow": lambda: astock.stock_fund_flow_120d(code)[-10:],
            "concepts": lambda: astock.concept_blocks(code),
        }
        for key, fn in optional_calls.items():
            try:
                data[key] = fn()
            except Exception as exc:  # noqa: BLE001 - data gaps should be explicit
                data[key] = {"error": str(exc)}
        return data

    def _a_share_detail(self, payload: dict) -> dict:
        code = self._required_str(payload, "code")
        data = {
            "code": code,
            "quote": astock.tencent_quote([code]).get(code),
        }
        optional_calls = {
            "financials": lambda: astock.financials(code),
            "announcements": lambda: astock.announcements(code),
            "reports": lambda: astock.eastmoney_reports(code, max_pages=1)[:10],
            "concepts": lambda: astock.concept_blocks(code),
            "holder_num_change": lambda: astock.holder_num_change(code, page_size=8),
            "hot_concepts": lambda: astock.hot_concepts(code),
            "investor_qa": lambda: astock.investor_qa(code, page_size=12),
        }
        data.update(self._run_optional_calls(optional_calls))
        data["fund_flow"] = []
        return data

    def _a_share_kline(self, payload: dict) -> dict:
        code = self._required_str(payload, "code")
        data = {"code": code}
        optional_calls = {
            "daily_kline": lambda: astock.kline(code, category=4, offset=90),
        }
        for key, fn in optional_calls.items():
            try:
                data[key] = fn()
            except Exception as exc:  # noqa: BLE001 - chart failures should not break detail
                data[key] = {"error": str(exc)}
        return data

    def _global_stock(self, payload: dict) -> dict:
        symbol = self._required_str(payload, "symbol")
        return gstock.us_hk_stock(symbol) or {"error": "symbol not found"}

    def _global_stock_quote(self, payload: dict) -> dict:
        symbol = self._required_str(payload, "symbol")
        return gstock.us_hk_quote(symbol) or {"error": "symbol not found"}

    def _global_stock_kline(self, payload: dict) -> dict:
        symbol = self._required_str(payload, "symbol")
        return gstock.us_hk_kline(symbol)

    def _company_evidence(self, payload: dict) -> dict:
        ticker = self._required_str(payload, "ticker")
        market_name = str(payload.get("market") or "UNKNOWN").strip().upper()
        company_name = str(payload.get("name") or ticker).strip()
        limit = max(1, min(int(payload.get("limit") or 8), 20))
        items: list[dict] = []
        errors: list[str] = []

        def add_rows(rows, kind: str, source: str) -> None:
            if not isinstance(rows, list):
                return
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                title = self._first_value(row, "title", "新闻标题", "公告标题", "报告名称")
                if not title:
                    continue
                published_at = self._first_value(
                    row, "published_at", "date", "time", "发布时间", "公告日期", "publishDate"
                )
                url = self._first_value(row, "url", "link", "新闻链接", "公告链接")
                provider = self._first_value(row, "source", "文章来源", "orgSName") or source
                snippet = self._first_value(row, "summary", "content", "新闻内容", "摘要") or ""
                items.append(
                    {
                        "id": f"{market_name.lower()}-{ticker}-{kind}-{len(items)}-{index}",
                        "kind": kind,
                        "title": title,
                        "source": provider,
                        "timestamp": published_at,
                        "url": url,
                        "snippet": snippet,
                        "relatedTicker": ticker,
                        "relatedCompany": company_name,
                        "provider": source,
                    }
                )

        if market_name == "A":
            calls = {
                "news": lambda: astock.stock_news(ticker, limit=limit),
                "announcement": lambda: astock.announcements(ticker, limit=limit),
                "report": lambda: astock.eastmoney_reports(ticker, max_pages=1)[:limit],
            }
            for kind, fn in calls.items():
                try:
                    add_rows(fn(), kind, "eastmoney")
                except Exception as exc:  # noqa: BLE001 - return partial evidence
                    errors.append(f"{kind}: {exc}")
        else:
            try:
                add_rows(gstock.company_news(ticker, limit=limit), "news", "yahoo")
            except Exception as exc:  # noqa: BLE001 - return an explicit partial result
                errors.append(f"news: {exc}")

        deduped = []
        seen = set()
        for item in items:
            key = (str(item.get("url") or "").strip(), str(item.get("title") or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        # Preserve source diversity instead of allowing the first provider
        # (usually news) to consume the entire result limit.
        buckets: dict[str, list[dict]] = {}
        for item in deduped:
            buckets.setdefault(str(item.get("kind") or "other"), []).append(item)
        selected = []
        kind_order = ["announcement", "news", "report"] + [
            kind for kind in buckets if kind not in {"announcement", "news", "report"}
        ]
        while len(selected) < limit and any(buckets.values()):
            for kind in kind_order:
                bucket = buckets.get(kind) or []
                if bucket and len(selected) < limit:
                    selected.append(bucket.pop(0))
        return {"ticker": ticker, "market": market_name, "items": selected, "errors": errors}

    def _market_overview(self, payload: dict) -> dict:
        scope = str(payload.get("scope") or "overview")
        if scope == "indices":
            return {"indices": astock.index_quote()}
        if scope == "global":
            return {"global_indices": market.get_global_indices()}
        if scope == "emotion":
            return market.get_short_term_emotion()
        if scope == "turnover":
            return market.get_turnover_top()
        if scope != "overview":
            raise SkillInvalidPayloadError(
                "market_overview scope must be one of overview, indices, global, emotion, turnover"
            )
        return market.get_overview()

    def _news_radar(self, payload: dict) -> dict:
        data = newsradar.get_radar(force=bool(payload.get("force", False)))
        track = str(payload.get("track") or "").strip()
        per_track = max(1, min(int(payload.get("per_track") or 5), 20))
        items = []
        total_cached = 0
        for industry in data.get("industries", []):
            industry_items = industry.get("items") or []
            total_cached += len(industry_items)
            name = industry.get("name", "")
            if track and track not in name:
                continue
            for item in industry_items[:per_track]:
                items.append(
                    {
                        "track": name,
                        "title": item.get("title"),
                        "time": item.get("time"),
                        "source": item.get("source"),
                        "url": item.get("url"),
                    }
                )
        return {
            "generated_at": data.get("generated_at"),
            "total_cached": total_cached,
            "tracks": [industry.get("name") for industry in data.get("industries", [])],
            "items": items,
        }

    def _industry_reports(self, payload: dict) -> list:
        keywords = payload.get("keywords")
        if keywords is not None and not isinstance(keywords, list):
            raise SkillInvalidPayloadError("industry_reports 'keywords' must be a list when provided")
        days = int(payload.get("days") or 90)
        rows = astock.eastmoney_industry_reports(keywords=keywords, days=days, max_pages=1)
        return [
            {
                "title": row.get("title"),
                "publishDate": row.get("publishDate"),
                "orgSName": row.get("orgSName"),
                "industryName": row.get("industryName"),
            }
            for row in rows[:20]
        ]

    @staticmethod
    def _required_str(payload: dict, key: str) -> str:
        value = str(payload.get(key) or "").strip()
        if not value:
            raise SkillInvalidPayloadError(f"missing required '{key}'")
        return value

    @staticmethod
    def _first_value(row: dict, *keys: str):
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip():
                return value
        return None

    def _cached(self, query_type: str, payload: dict, handler) -> dict:
        ttl = {
            "a_share_quote": self._QUOTE_TTL,
            "a_share_kline": self._KLINE_TTL,
            "a_share_detail": self._DETAIL_TTL,
            "global_stock_quote": self._QUOTE_TTL,
            "global_stock_kline": self._KLINE_TTL,
            "global_stock": self._QUOTE_TTL,
            "company_evidence": self._DETAIL_TTL,
        }.get(query_type, 0)
        if ttl <= 0:
            return handler(payload)

        key = f"{query_type}:{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
        now = time.time()
        hit = self._CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]

        data = handler(payload)
        if data and not data.get("error"):
            self._CACHE[key] = (now, data)
        return data

    @staticmethod
    def _run_optional_calls(optional_calls: dict) -> dict:
        results = {}
        with ThreadPoolExecutor(max_workers=min(len(optional_calls), 6)) as executor:
            futures = {executor.submit(fn): key for key, fn in optional_calls.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as exc:  # noqa: BLE001 - expose explicit missing data
                    results[key] = {"error": str(exc)}
        return results
