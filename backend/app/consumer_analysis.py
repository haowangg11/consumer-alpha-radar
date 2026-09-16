import json
import os
import time
import uuid
from typing import Iterable

import requests

from app.skills.market_data_skill import MarketDataSkill


STEP_LABELS = {
    "parse_signal": "解析消费信号",
    "expand_thesis": "扩展消费假设",
    "map_companies": "映射上市公司",
    "pull_evidence": "拉取证据",
    "score_line": "评估研究线",
    "debate_round": "多空研讨",
    "draft_brief": "生成机会简报",
}

SECTION_TITLES = {
    "signal_summary": "信号摘要",
    "consumer_thesis": "消费逻辑",
    "investment_hypothesis": "机会假设",
    "candidate_map": "候选公司",
    "evidence_scorecard": "证据评分",
    "risk_disconfirmation": "风险与反证",
    "next_verification": "下一步验证",
}

AGENT_ROLES = {
    "signal_analyst": "消费信号分析师",
    "category_strategist": "品类策略员",
    "company_mapper": "上市公司映射员",
    "evidence_researcher": "证据研究员",
    "bull_analyst": "多头分析师",
    "bear_analyst": "空头分析师",
    "valuation_analyst": "估值行情分析师",
    "risk_reviewer": "风险审查员",
    "committee": "投资委员会",
}


def _event(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _start(step: str) -> str:
    return _event({"type": "step_started", "step": step, "label": STEP_LABELS[step]})


def _delta(step: str, message: str) -> str:
    return _event({"type": "step_delta", "step": step, "message": message})


def _done(step: str) -> str:
    return _event({"type": "step_done", "step": step})


def _agent(role: str, stance: str, message: str, step: str, payload: dict | None = None) -> str:
    return _event(
        {
            "type": "agent_message",
            "agent": role,
            "agent_label": AGENT_ROLES.get(role, role),
            "stance": stance,
            "step": step,
            "message": message,
            "payload": payload or {},
        }
    )


def _short_text(value, fallback: str = "暂无可读结论") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _load_backend_env() -> dict:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    values = {}
    try:
        with open(env_path, "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return values


def _resolve_llm(llm: dict) -> dict:
    env = _load_backend_env()
    return {
        "provider": llm.get("provider") or env.get("LLM_PROVIDER") or "deepseek",
        "baseURL": llm.get("baseURL") or env.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1",
        "apiKey": llm.get("apiKey") or os.environ.get("DEEPSEEK_API_KEY") or env.get("DEEPSEEK_API_KEY") or "",
        "model": llm.get("model") or env.get("DEEPSEEK_MODEL") or "deepseek-chat",
    }


def _require_model(llm: dict) -> str | None:
    resolved = _resolve_llm(llm)
    if not resolved.get("baseURL") or not resolved.get("apiKey") or not resolved.get("model"):
        return "Connect a model in Preferences or configure DEEPSEEK_API_KEY in backend/.env."
    return None


def _chat_json(llm: dict, system: str, user: str) -> dict:
    llm = _resolve_llm(llm)
    base_url = str(llm["baseURL"]).rstrip("/")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {llm['apiKey']}",
            "Content-Type": "application/json",
        },
        json={
            "model": llm["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _as_object(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    return {}


def _extract_list(value, *keys: str) -> list:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, list):
            return candidate
    for key in ("data", "result", "items"):
        nested = value.get(key)
        if isinstance(nested, list):
            return nested
        if isinstance(nested, dict):
            extracted = _extract_list(nested, *keys)
            if extracted:
                return extracted
    return []


def _extract_sections(brief: dict) -> dict:
    sections = brief.get("sections") if isinstance(brief, dict) else {}
    if isinstance(sections, dict):
        return sections
    if isinstance(sections, list):
        out = {}
        for item in sections:
            if not isinstance(item, dict):
                continue
            key = item.get("id") or item.get("key")
            body = item.get("body") or item.get("content") or item.get("text")
            if key:
                out[str(key)] = body or ""
        return out
    return brief if isinstance(brief, dict) else {}


def _candidate_id(candidate: dict) -> str:
    ticker = str(candidate.get("ticker") or candidate.get("name") or "unknown").strip()
    market = _normalize_market(candidate.get("market"), ticker)
    return f"{market}:{ticker}"


def _normalize_market(market: str | None, ticker: str | None = None) -> str:
    ticker_text = str(ticker or "").strip()
    market_text = str(market or "").strip().upper()
    if ticker_text.isdigit() and len(ticker_text) == 6:
        return "A"
    if market_text in ("A", "HK", "US", "KR", "UNKNOWN"):
        return market_text
    if ticker_text.isdigit() and 4 <= len(ticker_text) <= 5:
        return "HK"
    return market_text or "UNKNOWN"


def _normalize_exposure(value: str) -> str:
    value = str(value or "").lower()
    if value in ("direct", "adjacent", "weak"):
        return value
    return "weak"


def _normalize_decision(value: str) -> str:
    value = str(value or "").lower()
    if value in ("track", "watch", "continue", "跟踪", "继续跟踪"):
        return "track"
    if value in ("pause", "hold", "wait", "暂缓", "观察"):
        return "pause"
    if value in ("drop", "reject", "remove", "剔除", "放弃"):
        return "drop"
    return "pause"


def _quote_from_snapshot(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        return {}
    quote = snapshot.get("quote") or snapshot
    if not isinstance(quote, dict):
        return {}
    return {
        "price": quote.get("price"),
        "change_pct": quote.get("change_pct") or quote.get("change_pct"),
        "pe_ttm": quote.get("pe_ttm"),
        "pb": quote.get("pb"),
    }


def _evidence_from_market_news(items: list) -> list:
    out = []
    for idx, item in enumerate(items[:8]):
        out.append(
            {
                "id": f"news-{idx}",
                "kind": "news",
                "title": item.get("title") or "Sector news",
                "source": item.get("source") or "news radar",
                "timestamp": item.get("time"),
                "url": item.get("url") or item.get("link"),
                "relevance": f"Sector context from {item.get('track', 'consumer/market news')}.",
                "snippet": item.get("title") or "",
            }
        )
    return out


def _company_evidence_items(result: dict, candidate: dict) -> list:
    data = result.get("data") if isinstance(result, dict) else {}
    rows = data.get("items") if isinstance(data, dict) else []
    out = []
    for index, item in enumerate(rows or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                **item,
                "id": item.get("id") or f"company-evidence-{candidate['id']}-{index}",
                "relatedTicker": candidate.get("ticker"),
                "relatedMarket": candidate.get("market"),
                "relatedCompany": candidate.get("name"),
                "relevance": f"与 {candidate.get('name')} 的公开公司动态直接相关。",
            }
        )
    return out


def _find_candidate(candidates: list[dict], item: dict) -> dict | None:
    ticker = str(item.get("ticker") or "").strip()
    market = str(item.get("market") or "").strip()
    name = str(item.get("name") or "").strip()
    for candidate in candidates:
        if ticker and str(candidate.get("ticker") or "").strip() == ticker:
            return candidate
        if market and ticker and candidate.get("id") == f"{market}:{ticker}":
            return candidate
        if name and str(candidate.get("name") or "").strip() == name:
            return candidate
    return None


def _fallback_decision(candidate: dict) -> str:
    if candidate.get("exposure") == "direct" and candidate.get("confidence") == "high":
        return "track"
    return "pause"


def stream_consumer_analysis(payload: dict) -> Iterable[str]:
    run_id = str(uuid.uuid4())[:8]
    market_data = MarketDataSkill()
    signal = str(payload.get("signal") or "").strip()
    market_scope = payload.get("market_scope") or "ALL"
    mode = payload.get("mode") or "full"
    llm = _resolve_llm(payload.get("llm") or {})

    yield _event({"type": "run_started", "run_id": run_id})

    missing_model = _require_model(llm)
    if missing_model:
        yield _event({"type": "error", "code": "needs_model", "message": missing_model})
        return
    if not signal:
        yield _event({"type": "error", "code": "empty_signal", "message": "Signal cannot be empty."})
        return

    yield _start("parse_signal")
    yield _delta("parse_signal", "正在读取消费观察，抽取消费品、品牌、品类和使用场景。")
    parse = _chat_json(
        llm,
        "Return strict JSON for a consumer-product investment radar. Do not recommend buying. "
        "Extract product, brand, category, consumer_scene, keywords, and concise interpretation.",
        json.dumps({"signal": signal, "market_scope": market_scope, "mode": mode}, ensure_ascii=False),
    )
    parse = _as_object(parse)
    parsed_label = parse.get("product") or parse.get("brand") or parse.get("category") or signal
    parsed_scene = parse.get("consumer_scene") or parse.get("interpretation") or "需要继续验证消费场景。"
    yield _agent(
        "signal_analyst",
        "observation",
        f"我把输入识别为「{parsed_label}」相关消费信号。当前核心场景是：{parsed_scene}",
        "parse_signal",
        {"parsed_signal": parse},
    )
    yield _done("parse_signal")

    yield _start("expand_thesis")
    thesis_keywords = parse.get("keywords") or [parse.get("category") or parse.get("brand") or signal]
    track = str(thesis_keywords[0] or "")
    yield _delta("expand_thesis", f"已扩展到消费品类上下文：{track}。")
    yield _agent(
        "category_strategist",
        "hypothesis",
        f"我会先按「{track or parsed_label}」这条品类线寻找资讯和产业链线索，而不是直接跳到股票推荐。",
        "expand_thesis",
        {"keywords": thesis_keywords},
    )
    market_news = market_data.run("news_radar", {"track": track, "per_track": 5})
    yield _done("expand_thesis")

    yield _start("map_companies")
    yield _delta("map_companies", "正在要求模型只返回可用公开数据验证的上市公司候选。")
    mapping = _chat_json(
        llm,
        "Return strict JSON with candidates only. Each candidate must be a listed company plausibly tied to the consumer signal. "
        "Use markets A, HK, US, or KR. Fields: name, ticker, market, exposure(direct|adjacent|weak), why, confidence(high|medium|low). "
        "Do not invent if unsure; return fewer candidates.",
        json.dumps({"signal": signal, "parsed_signal": parse, "market_scope": market_scope}, ensure_ascii=False),
    )
    candidates = _extract_list(mapping, "candidates", "companies")
    normalized_candidates = []
    for candidate in candidates[:8]:
        if not isinstance(candidate, dict):
            continue
        normalized = {
            "id": _candidate_id(candidate),
            "name": candidate.get("name") or candidate.get("ticker") or "Unknown",
            "ticker": str(candidate.get("ticker") or "").strip(),
            "market": _normalize_market(candidate.get("market"), candidate.get("ticker")),
            "exposure": _normalize_exposure(candidate.get("exposure")),
            "why": candidate.get("why") or "Model mapped this company to the consumer signal.",
            "confidence": candidate.get("confidence") if candidate.get("confidence") in ("high", "medium", "low") else "low",
        }
        normalized_candidates.append(normalized)
        yield _event({"type": "candidate_found", "candidate": normalized})
        yield _agent(
            "company_mapper",
            "mapping",
            f"候选标的：{normalized['name']}（{normalized['market']} · {normalized['ticker'] or '未给代码'}）。关联强度：{normalized['exposure']}。理由：{normalized['why']}",
            "map_companies",
            {"candidate": normalized},
        )
    yield _done("map_companies")

    yield _start("pull_evidence")
    evidence = []
    news_items = ((market_news.get("data") or {}).get("items") or []) if isinstance(market_news, dict) else []
    yield _agent(
        "evidence_researcher",
        "evidence",
        f"资讯侧先拿到 {len(news_items)} 条与「{track or parsed_label}」相关的公开消息，下面只把真实来源写入证据库。",
        "pull_evidence",
        {"news_count": len(news_items)},
    )
    for item in _evidence_from_market_news(news_items):
        evidence.append(item)
        yield _event({"type": "evidence_found", "evidence": item})

    enriched_candidates = []
    for candidate in normalized_candidates:
        ticker = candidate["ticker"]
        market = candidate["market"]
        if not ticker:
            enriched_candidates.append(candidate)
            continue
        if market == "A":
            snapshot = market_data.run("a_share_snapshot", {"code": ticker})
        else:
            snapshot = market_data.run("global_stock", {"symbol": ticker})
        company_evidence = market_data.run(
            "company_evidence",
            {
                "ticker": ticker,
                "market": market,
                "name": candidate.get("name"),
                "aliases": [candidate.get("name"), ticker],
                "limit": 6,
            },
        )
        data = snapshot.get("data") if isinstance(snapshot, dict) else {}
        candidate = {**candidate, "quote": _quote_from_snapshot(data or {})}
        enriched_candidates.append(candidate)
        evidence_item = {
            "id": f"company-{candidate['id']}",
            "kind": "company",
            "title": f"{candidate['name']} public-market snapshot",
            "source": "market_data",
            "relatedTicker": ticker,
            "relevance": candidate["why"],
            "snippet": json.dumps(data, ensure_ascii=False)[:900],
        }
        evidence.append(evidence_item)
        yield _event({"type": "candidate_found", "candidate": candidate})
        yield _event({"type": "evidence_found", "evidence": evidence_item})
        direct_evidence = _company_evidence_items(company_evidence, candidate)
        for direct_item in direct_evidence:
            evidence.append(direct_item)
            yield _event({"type": "evidence_found", "evidence": direct_item})
        yield _agent(
            "valuation_analyst",
            "market",
            f"已拉取 {candidate['name']} 的行情快照和 {len(direct_evidence)} 条公司新闻/公告/研报。价格：{candidate.get('quote', {}).get('price', '暂无')}，涨跌幅：{candidate.get('quote', {}).get('change_pct', '暂无')}，PE(TTM)：{candidate.get('quote', {}).get('pe_ttm', '暂无')}。",
            "pull_evidence",
            {"candidate": candidate},
        )
        time.sleep(0.05)
    yield _done("pull_evidence")

    yield _start("score_line")
    yield _delta("score_line", "正在根据候选相关性、证据覆盖和数据缺口评估研究线成熟度。")
    score_input = {
        "parsed_signal": parse,
        "candidates": enriched_candidates,
        "evidence": evidence,
    }
    score = _chat_json(
        llm,
        "Return strict JSON: maturity must be one of Emerging, Supported, Validated, Stretched, Insufficient, Broken. "
        "Also include a short reason. Score research-line maturity, not buy attractiveness.",
        json.dumps(score_input, ensure_ascii=False),
    )
    score = _as_object(score)
    maturity = score.get("maturity") or "Insufficient"
    yield _agent(
        "risk_reviewer",
        "review",
        f"研究线成熟度暂定为「{maturity}」。原因：{_short_text(score.get('reason'))}",
        "score_line",
        {"maturity": maturity, "reason": score.get("reason")},
    )
    yield _done("score_line")

    yield _start("debate_round")
    yield _delta("debate_round", "正在让多头、空头、估值和委员会分别审视每个候选公司。")
    debate = _chat_json(
        llm,
        "Return strict JSON for a Consumer Alpha Radar debate. Do not give buy/sell advice. "
        "For each candidate, include: name, ticker, market, bull, bear, valuation, risk, "
        "decision(track|pause|drop), decision_reason. Also include committee_summary. "
        "Use concise Chinese prose and cite only evidence present in the input.",
        json.dumps(
            {
                "signal": signal,
                "parsed_signal": parse,
                "maturity": maturity,
                "score_reason": score.get("reason"),
                "candidates": enriched_candidates,
                "evidence": evidence,
            },
            ensure_ascii=False,
        ),
    )
    debate = _as_object(debate)
    debate_cases = _extract_list(debate, "cases", "debates", "companies")
    if not debate_cases and enriched_candidates:
        debate_cases = [
            {
                "name": candidate.get("name"),
                "ticker": candidate.get("ticker"),
                "market": candidate.get("market"),
                "bull": debate.get("bull") or candidate.get("why"),
                "bear": debate.get("bear") or debate.get("risk"),
                "valuation": debate.get("valuation"),
                "risk": debate.get("risk") or debate.get("committee_summary"),
                "decision": debate.get("decision") or _fallback_decision(candidate),
                "decision_reason": debate.get("decision_reason") or debate.get("committee_summary"),
            }
            for candidate in enriched_candidates
        ]
    for debate_case in debate_cases:
        if not isinstance(debate_case, dict):
            continue
        candidate = _find_candidate(enriched_candidates, debate_case)
        if candidate is None:
            continue
        candidate_debate = {
            "bull": _short_text(debate_case.get("bull"), "多头理由不足。"),
            "bear": _short_text(debate_case.get("bear"), "空头理由不足。"),
            "valuation": _short_text(debate_case.get("valuation"), "估值信息不足。"),
            "risk": _short_text(debate_case.get("risk"), "风险信息不足。"),
            "decision": _normalize_decision(debate_case.get("decision")),
            "decision_reason": _short_text(debate_case.get("decision_reason"), "需要继续验证。"),
        }
        candidate["debate"] = candidate_debate
        label = f"{candidate['name']}（{candidate['market']} · {candidate['ticker']}）"
        yield _agent("bull_analyst", "bull", f"{label}：{candidate_debate['bull']}", "debate_round", {"candidate": candidate})
        yield _agent("bear_analyst", "bear", f"{label}：{candidate_debate['bear']}", "debate_round", {"candidate": candidate})
        yield _agent("valuation_analyst", "market", f"{label}：{candidate_debate['valuation']}", "debate_round", {"candidate": candidate})
        yield _agent("risk_reviewer", "review", f"{label}：{candidate_debate['risk']}", "debate_round", {"candidate": candidate})
        yield _agent(
            "committee",
            "decision",
            f"{label}：{candidate_debate['decision_reason']} 结论：{candidate_debate['decision']}。",
            "debate_round",
            {"candidate": candidate},
        )
        yield _event({"type": "candidate_found", "candidate": candidate})
    yield _agent(
        "committee",
        "decision",
        _short_text(debate.get("committee_summary"), "本轮多空研讨已完成，等待简报生成。"),
        "debate_round",
        {"maturity": maturity, "candidate_count": len(enriched_candidates)},
    )
    yield _done("debate_round")

    yield _start("draft_brief")
    yield _delta("draft_brief", "正在基于真实证据生成消费机会简报。")
    brief = _chat_json(
        llm,
        "Return strict JSON with sections object containing exactly these keys: signal_summary, consumer_thesis, "
        "investment_hypothesis, candidate_map, evidence_scorecard, risk_disconfirmation, next_verification. "
        "Each value should be concise prose. No buy/sell instruction.",
        json.dumps({**score_input, "maturity": maturity, "score_reason": score.get("reason"), "debate": debate}, ensure_ascii=False),
    )
    brief = _as_object(brief)
    sections = []
    section_values = _extract_sections(brief)
    yield _agent(
        "bull_analyst",
        "bull",
        _short_text(section_values.get("investment_hypothesis"), "多头假设不足，需要更多消费数据和公司验证。"),
        "draft_brief",
        {"section": "investment_hypothesis"},
    )
    yield _agent(
        "bear_analyst",
        "bear",
        _short_text(section_values.get("risk_disconfirmation"), "反方证据不足，暂时不能确认风险是否已被覆盖。"),
        "draft_brief",
        {"section": "risk_disconfirmation"},
    )
    for key, title in SECTION_TITLES.items():
        section = {"id": key, "title": title, "body": str(section_values.get(key) or "")}
        sections.append(section)
        yield _event({"type": "brief_section", "section": section, "maturity": maturity})
    yield _done("draft_brief")
    yield _agent(
        "committee",
        "decision",
        f"本轮研讨完成：共形成 {len(enriched_candidates)} 个候选公司、{len(evidence)} 条证据，研究线状态为「{maturity}」。下一步应优先验证消费热度是否能传导到公司收入或预期。",
        "draft_brief",
        {"candidate_count": len(enriched_candidates), "evidence_count": len(evidence), "maturity": maturity},
    )

    result = {
        "run_id": run_id,
        "maturity": maturity,
        "sections": sections,
        "candidates": enriched_candidates,
        "evidence": evidence,
    }
    yield _event({"type": "done", "result": result})
