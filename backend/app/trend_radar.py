import hashlib
import re
from typing import Any

from app.data_sources.vibe_research import newsradar


CONSUMER_INDUSTRY_KEYS = {"consumer"}
SOFT_ALLOW_INDUSTRY_KEYS = {"macro", "tech", "bio"}
BLOCKED_TOPIC_KEYS = {
    "ai", "openai", "microsoft", "prompt", "moonshot", "groclm", "teaching", "case", "cutting",
    "google", "what",
}

CONSUMER_KEYWORDS = {
    "中文": [
        "消费", "品牌", "零售", "电商", "直播", "潮玩", "玩具", "美妆", "护肤", "化妆品", "香水",
        "服饰", "鞋", "运动", "户外", "母婴", "宠物", "食品", "饮料", "咖啡", "茶饮", "酒",
        "家电", "小家电", "手机", "耳机", "平板", "相机", "游戏机", "穿戴", "智能手表", "家居",
        "餐饮", "旅游", "酒店", "免税", "奢侈品", "黄金", "珠宝", "医美", "个护", "保健品",
    ],
    "english": [
        "retail", "ecommerce", "e-commerce", "apparel",
        "beauty", "skincare", "cosmetic", "fragrance", "luxury", "fashion", "sneaker", "sportswear",
        "toy", "gaming console", "smartphone", "iphone", "android", "wearable", "headphone", "camera",
        "tablet", "tab", "buds", "galaxy", "pixel", "ipad", "macbook", "airpods", "osmo", "dji",
        "nike", "adidas", "columbia", "starbucks", "shein", "temu",
        "home appliance", "coffee", "tea", "beverage", "food", "restaurant", "travel", "hotel",
        "pet", "baby", "wellness", "personal care", "jewelry",
    ],
}

CONSUMER_EXCLUDE_KEYWORDS = [
    "openai", "microsoft", "anthropic", "hugging face", "cyber", "semiconductor", "chip", "gpu",
    "model", "llm", "ai agent", "kubernetes", "developer", "security", "ransomware", "nasa",
    "rocket", "arxiv", "quantum", "solar", "battery", "oil", "pharma trial",
    "大模型", "半导体", "芯片", "算力", "网络安全", "航天", "火箭", "论文", "光伏", "储能", "消费税",
]


def _is_consumer_item(industry_key: str, text: str) -> bool:
    lower = text.lower()
    chinese_hit = any(word in text for word in CONSUMER_KEYWORDS["中文"])
    english_hit = any(
        re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", lower)
        for word in CONSUMER_KEYWORDS["english"]
    )
    consumer_hit = chinese_hit or english_hit
    if any(word in lower for word in CONSUMER_EXCLUDE_KEYWORDS):
        return False
    if industry_key in CONSUMER_INDUSTRY_KEYS:
        return consumer_hit
    if industry_key not in SOFT_ALLOW_INDUSTRY_KEYS:
        return False
    return consumer_hit


def _consumer_topic_label(text: str, fallback: str) -> str:
    labels = [
        ("黄金珠宝", ["黄金", "金饰", "珠宝", "jewelry"]),
        ("健康管理", ["减重", "饮食", "热量", "营养", "wellness", "personal care"]),
        ("手机平板", ["手机", "平板", "smartphone", "pixel", "galaxy", "iphone", "android"]),
        ("耳机穿戴", ["耳机", "buds", "wearable", "watch"]),
        ("影像相机", ["相机", "camera"]),
        ("家电数码", ["家电", "小家电", "appliance"]),
        ("电商零售", ["电商", "零售", "e-commerce", "ecommerce", "retail"]),
        ("美妆护肤", ["美妆", "护肤", "skincare", "beauty", "cosmetic"]),
        ("食品饮料", ["食品", "饮料", "咖啡", "茶饮", "food", "beverage", "coffee"]),
    ]
    lower = text.lower()
    for label, keywords in labels:
        if any(keyword in text or keyword in lower for keyword in keywords):
            return label
    return fallback


def _tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens = re.findall(r"[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]{2,}", text)
    stop = {"the", "and", "for", "with", "from", "into", "that", "this", "今天", "近期", "最新"}
    return [token for token in tokens if token not in stop]


def _topic_key(item: dict[str, Any]) -> str:
    title = item.get("title") or ""
    summary = item.get("summary") or ""
    consumer_label = _consumer_topic_label(f"{title} {summary}", "")
    if consumer_label:
        return consumer_label
    tokens = _tokenize(title)
    if tokens:
        return tokens[0][:18]
    return (item.get("source") or "未分类")[:18]


def trend_radar_topics(keyword: str = "", limit: int = 24, per_topic: int = 100, refresh: bool = False) -> dict:
    radar = newsradar.get_radar(force=refresh)
    rows: list[dict[str, Any]] = []
    for industry in radar.get("industries") or []:
        industry_key = industry.get("key") or ""
        for item in industry.get("items") or []:
            item_text = f"{item.get('title') or ''} {item.get('summary') or ''}"
            if not _is_consumer_item(industry_key, item_text):
                continue
            search_text = f"{item_text} {industry.get('name') or ''}"
            if keyword and keyword.lower() not in search_text.lower():
                continue
            rows.append(
                {
                    **item,
                    "industry": industry.get("name"),
                    "industry_key": industry.get("key"),
                    "accent": industry.get("accent"),
                }
            )

    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(_topic_key(row), []).append(row)

    topics = []
    for key, items in buckets.items():
        if key.lower() in BLOCKED_TOPIC_KEYS:
            continue
        sources = sorted({item.get("source") or "unknown" for item in items})
        industries = sorted({item.get("industry") or "未分类" for item in items})
        digest = "；".join((item.get("title") or "")[:64] for item in items[:2])
        heat = min(100, 38 + len(items) * 9 + len(sources) * 6 + len(industries) * 4)
        first = min((item.get("time") or "" for item in items), default="")
        latest = max((item.get("time") or "" for item in items), default="")
        topic_id = hashlib.sha1(f"{key}:{digest}".encode("utf-8")).hexdigest()[:10]
        topics.append(
            {
                "id": topic_id,
                "topic": key,
                "heat_score": heat,
                "sources": sources,
                "industries": industries,
                "first_seen": first,
                "latest_seen": latest,
                "summary": digest or f"{key} 相关资讯聚合",
                "items": items[: max(1, min(per_topic, 200))],
                "lifecycle": [
                    {"stage": "捕获", "at": first, "note": f"{len(sources)} 个来源进入雷达"},
                    {"stage": "归并", "at": latest, "note": f"合并为 {len(items)} 条相关资讯"},
                    {"stage": "承接", "at": latest, "note": "可交给雷达助手生成消费投资信号"},
                ],
            }
        )

    topics.sort(key=lambda topic: (topic["heat_score"], len(topic["items"])), reverse=True)
    return {
        "generated_at": radar.get("generated_at"),
        "recent_days": radar.get("recent_days"),
        "source_stats": radar.get("stats"),
        "topics": topics[: max(1, min(limit, 50))],
    }
