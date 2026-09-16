from app.data_sources.vibe_research import astock, gstock, newsradar
from app.skills.errors import SkillInvalidPayloadError
from app.skills.market_data_skill import MarketDataSkill


skill = MarketDataSkill()

orig_quote = astock.tencent_quote
orig_global = gstock.us_hk_stock
orig_company_news = gstock.company_news
orig_radar = newsradar.get_radar
orig_stock_news = astock.stock_news
orig_announcements = astock.announcements
orig_reports = astock.eastmoney_reports

try:
    astock.tencent_quote = lambda codes: {codes[0]: {"name": "贵州茅台", "price": 1200.0}}
    gstock.us_hk_stock = lambda symbol: {"code": symbol, "market": "US", "quote": {"price": 100.0}}
    gstock.company_news = lambda symbol, limit=10: [
        {"title": "Apple launches a new product", "source": "Example", "url": "https://example.com/apple"}
    ]
    astock.stock_news = lambda code, limit=20: [
        {"新闻标题": "公司发布新品", "文章来源": "东财", "新闻链接": "https://example.com/news"}
    ]
    astock.announcements = lambda code, limit=15: [
        {"title": "年度报告公告", "date": "2026-08-18", "url": "https://example.com/notice"}
    ]
    astock.eastmoney_reports = lambda code, max_pages=1: [
        {"title": "公司研究报告", "publishDate": "2026-08-17", "orgSName": "示例证券"}
    ]
    newsradar.get_radar = lambda force=False: {
        "generated_at": "2026-07-30 10:00",
        "industries": [
            {
                "name": "AI / 大模型",
                "items": [
                    {"title": "AI capex cycle update", "time": "07-30 09:00", "source": "Example"}
                ],
            }
        ],
    }

    quote = skill.run("a_share_quote", {"codes": ["600519"]})
    assert quote["status"] == "ok"
    assert quote["data"]["600519"]["name"] == "贵州茅台"

    global_stock = skill.run("global_stock", {"symbol": "AAPL"})
    assert global_stock["data"]["code"] == "AAPL"

    radar = skill.run("news_radar", {"track": "AI", "per_track": 1})
    assert radar["data"]["items"][0]["track"] == "AI / 大模型"

    a_evidence = skill.run("company_evidence", {"ticker": "600519", "market": "A", "name": "贵州茅台"})
    assert {item["kind"] for item in a_evidence["data"]["items"]} == {"news", "announcement", "report"}
    assert all(item["relatedTicker"] == "600519" for item in a_evidence["data"]["items"])

    us_evidence = skill.run("company_evidence", {"ticker": "AAPL", "market": "US", "name": "Apple"})
    assert us_evidence["data"]["items"][0]["kind"] == "news"
    assert us_evidence["data"]["items"][0]["relatedTicker"] == "AAPL"

    try:
        skill.run("unknown", {})
        raise AssertionError("expected SkillInvalidPayloadError")
    except SkillInvalidPayloadError:
        pass
finally:
    astock.tencent_quote = orig_quote
    gstock.us_hk_stock = orig_global
    gstock.company_news = orig_company_news
    newsradar.get_radar = orig_radar
    astock.stock_news = orig_stock_news
    astock.announcements = orig_announcements
    astock.eastmoney_reports = orig_reports

print("OK")
