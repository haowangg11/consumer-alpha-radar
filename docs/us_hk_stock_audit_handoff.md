# US/HK Stock Data Audit Handoff

Date: 2026-07-31

## Project

Consumer Alpha Radar is a personal Chinese consumer-investing radar. It is not a Bloomberg-like terminal; it starts from consumer products, brands, scenes, or news, then maps the signal to listed-company research lines across A/HK/US markets.

Core app path:

- Project root: `/Users/zzzzzzf/Downloads/Consumer-Alpha-Radar`
- Frontend: React + Vite + TypeScript in `frontend/`
- Backend: FastAPI in `backend/app/`
- Frontend dev server: `http://127.0.0.1:5898/`
- Backend API: `http://127.0.0.1:8000/`

Do not rely on screenshots or long chat history. Use this handoff plus code inspection and live verification.

## Current Product Shape

Main left-nav views:

- 雷达首页
- 热点雷达
- 机会简报
- 研讨室
- 证据库
- 个股行情
- 观察清单

The current task focuses only on the `个股行情` view.

## Recent Fixes Already Completed

### A-share code normalization

Problem found: A-share candidates could carry suffixes like `600415.SH`, but the app/data source expected pure `600415`.

Fixed in:

- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `backend/app/main.py`

Expected normalization:

- `600415.SH` -> `A / 600415`
- `002315.SZ` -> `A / 002315`
- `3690.HK` -> `HK / 3690`
- `BABA.US` -> `US / BABA`

### A-share quote and K-line speed

Relevant files:

- `backend/app/data_sources/vibe_research/astock.py`
- `backend/app/skills/market_data_skill.py`

Changes:

- A-share K-line now prefers Tencent quick source before Eastmoney/mootdx fallback.
- `MarketDataSkill` has short in-process cache for quote, K-line, and detail.
- Heavy A-share detail was reduced and parallelized.
- `fund_flow` was removed from initial A-share detail because it was the main cold-start drag and often returned empty.

Observed A-share results:

- `/api/stocks/A/600415.SH/quote` returns 小商品城 price normally.
- `/api/stocks/A/600415.SH/kline` returns 91 daily rows.
- UI shows latest price and chart for 小商品城 in under ~1s.
- Detail layer cold-start improved from roughly 8-10s to about 2.06s; cache hit about 0.003s.

## New Task

Audit and fix US/HK stock loading in the `个股行情` page.

User report:

- A-share is acceptable now.
- US and HK stocks currently have missing or very slow quote/K-line data.
- Need determine whether this is a data-source problem or our implementation problem.
- If it is our implementation, fix it.
- If the source lacks K-line or quote capability, document the limitation and add the best available fast fallback.

## What To Inspect

Frontend:

- `frontend/src/App.tsx`
  - `StocksPage`
  - `normalizeStockRef`
  - quote/K-line/detail state handling
- `frontend/src/api.ts`
  - `fetchStockQuote`
  - `fetchStockKline`
  - `fetchStockSnapshot`
  - `normalizeStockRoute`
- `frontend/src/types.ts`

Backend:

- `backend/app/main.py`
  - `/api/stocks/{market}/{ticker}`
  - `/api/stocks/{market}/{ticker}/quote`
  - `/api/stocks/{market}/{ticker}/kline`
  - `normalize_stock_route`
- `backend/app/skills/market_data_skill.py`
  - `_global_stock`
  - A-share handlers for comparison
- `backend/app/data_sources/vibe_research/gstock.py`
  - likely source for US/HK snapshots
- `backend/app/data_sources/vibe_research/market.py`
  - maybe related global index/source helpers

## Likely Issue To Confirm

Current backend behavior before this new audit likely is:

- A-share has dedicated quote and K-line endpoints.
- Non-A markets may call `global_stock` for quote/detail.
- Non-A `/kline` currently may return an empty `daily_kline: []`.

If that is true, the problem is mostly our implementation gap, not necessarily a data-source outage.

## Validation Targets

Use live API and UI where possible.

Example symbols from current app state:

- US: `PDD`
- US: `BABA`
- US: `JD`
- US: `VIPS`
- HK: `3690.HK` or normalized `3690`

For each representative market, record:

- Quote endpoint response and elapsed time.
- K-line endpoint response and elapsed time.
- UI behavior after selecting the stock in `个股行情`.
- Whether price metrics render.
- Whether chart renders.
- Console errors/warnings if any.

## Expected Deliverable

In the new task:

1. Diagnose whether US/HK issue is data-source limitation or app implementation.
2. Implement a focused fix if feasible.
3. Restart local services if needed.
4. Verify with API timings and UI observations.
5. Report exact changed files and timings.

Keep the scope tight: only `个股行情` US/HK quote/K-line behavior.
