# Consumer Alpha Radar

## Overview

Consumer Alpha Radar is an AI-native alternative data platform that discovers emerging consumer trends from internet signals and translates them into public market investment opportunities.

The platform connects:

Consumer behavior
→ Emerging trends
→ Business impact
→ Public companies
→ Investment insights


## Problem

Traditional equity research relies heavily on financial statements and quarterly reports.

However, consumer behavior changes faster than financial reporting cycles.

Early signals often appear in:

- Search behavior
- Online discussions
- Product reviews
- Social engagement


## Solution

Consumer Alpha Radar uses multiple AI agents to:

1. Detect emerging consumer trends
2. Understand consumer psychology
3. Map trends to public companies
4. Analyze financial impact
5. Generate investment research


## Core Architecture

Multi-Agent System:

- Trend Discovery Agent
- Consumer Psychology Agent
- Company Mapping Agent
- Financial Analysis Agent
- Risk Critic Agent
- Investment Committee Agent


## Technology Stack

Frontend:
- Next.js
- React
- TypeScript
- Tailwind CSS

Backend:
- Python
- FastAPI

AI:
- Multi-Agent Workflow
- LangGraph
- LLM Routing

Database:
- PostgreSQL
- Vector Database


## Vision

Build an AI-powered research assistant that helps investors discover market opportunities before they appear in traditional financial data.

## Cross-Market Data Sources

Consumer Alpha Radar now treats Vibe-Research as a reference data layer, not as a product template.
The copied data-source modules live under `backend/app/data_sources/vibe_research/` and expose:

- A-share quotes, valuation, financials, announcements, reports, funds, concepts, and industry data
- US / HK / KR quote snapshots and key metrics where available
- market overview, global indices, short-term sentiment, and turnover lists
- 12-track sector news radar backed by 108 public RSS sources

The product direction is still discovery-first: agents should convert objective data into
opportunity hypotheses, evidence, risks, and validation checklists, not into buy/sell instructions.
