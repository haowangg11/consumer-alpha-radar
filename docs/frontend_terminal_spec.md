# Consumer Alpha Terminal Frontend Spec

## Product Essence

Consumer Alpha Radar is a consumer-product investment opportunity radar. It starts from a concrete consumer observation, such as a product, brand, or consumption behavior, and turns it into a researchable public-market opportunity line.

It is not a generic financial terminal, not a semiconductor or macro radar, and not a buy/sell recommendation machine. It validates whether a consumer observation deserves further investment research.

## Experience Form

The frontend should feel like an Apple-inspired personal research terminal:

- light-first, with a dark professional mode
- premium macOS research app language, not a website dashboard
- fluid motion, translucent materials, spatial hierarchy, and precise typography
- information-dense enough to feel useful, but never a Bloomberg-style data wall

## Core User Flow

1. User describes a consumer product, brand, or phenomenon in natural language.
2. The system expands it into product/category/consumer-thesis terms.
3. The backend uses real public-market data sources to find and validate candidate listed companies.
4. The frontend streams the analysis process step by step.
5. The result is a Consumer Opportunity Brief with evidence, risks, candidates, and next verification tasks.

## Main Layout

The terminal is a full-height research OS:

- Top Research OS bar
- Left Codex-style Chat Console, default expanded
- Center Opportunity Brief Canvas, the visual focus
- Right Evidence Inspector
- Bottom Analysis Timeline step rail
- Preferences Sheet for model, data, appearance, and privacy

Desktop baseline dimensions:

- app shell: `100dvh`
- top bar: `52px`
- chat console: `340px`
- evidence inspector: `360px`
- timeline: `72px`
- center canvas: adaptive, minimum useful width around `560px`

## Opportunity Brief Canvas Structure

1. Signal Summary
2. Consumer Thesis
3. Investment Hypothesis
4. Candidate Map
5. Evidence Scorecard
6. Risk / Disconfirmation
7. Next Verification

The canvas follows the user's cognition path from consumer observation to investment research line, not a raw financial-data order.

## Chat Console

The left console is a Codex-style collapsible chat surface, not a form.

- Default expanded on desktop
- Natural-language input for consumer observations
- Light chips for market scope and analysis mode
- Streaming messages for run status and agent steps
- Follow-up questions should eventually update the current brief

## Evidence Inspector

Default state:

- data source readiness
- empty evidence stack
- concise message that evidence will appear as the brief is built

During analysis:

- step-level data fetching progress
- evidence items appear as they arrive

After analysis:

- tabs or filters for Companies, Reports, Announcements, Financials, Market, Risks
- expandable evidence items
- source, timestamp, related company, relevance, and raw snippet

## Analysis Timeline

The bottom rail is functional, not decorative.

Steps:

1. Parse Signal
2. Expand Thesis
3. Map Companies
4. Pull Evidence
5. Score Line
6. Draft Brief

States:

- waiting
- running
- done
- warning
- failed

Clicking a step should eventually filter the evidence and focus the matching brief section.

## Candidate Map

Candidates are shown as a map, not a ranked stock list.

Groups:

- Direct Exposure
- Adjacent Exposure
- Weak / Watch

Each candidate shows:

- ticker / company / market
- exposure type
- why linked
- evidence count
- latest quote snapshot when available
- exposure confidence, not buy confidence

## Scoring

Core score: `Signal Maturity`.

This measures whether the consumer observation has matured into a researchable investment line. It is not a stock buy score.

States:

- Emerging
- Supported
- Validated
- Stretched
- Insufficient
- Broken

## Visual System

Material tokens:

- `surface-base`
- `surface-glass`
- `surface-floating`
- `surface-focus`
- `surface-dim`

Depth tokens:

- `depth-0`
- `depth-1`
- `depth-2`
- `depth-3`
- `depth-4`

Motion tokens:

- `spring-soft`
- `spring-snappy`
- `spring-drag`
- `fade-quick`
- `blur-materialize`

Colors:

- Light base: cold white, silver grey, graphite
- Dark base: graphite black, dark glass, near white
- Main accent: electric blue
- Emerging: soft blue
- Supported: teal / cyan
- Validated: signal green
- Stretched: soft amber
- Insufficient: cool grey
- Broken: soft rose

## Settings

Preferences Sheet tabs:

- Model
- Data
- Appearance
- Privacy

MVP stores model configuration in browser localStorage and sends it with each analyze request. The backend should not persist API keys.

## Data Principle

No mock data in the product path.

The frontend calls the real streaming API. If the backend lacks model configuration or a data source is unavailable, the UI must show real setup, limited, empty, or error states.

Primary API:

`POST /api/analyze-consumer-signal/stream`

Event types:

- `run_started`
- `step_started`
- `step_delta`
- `candidate_found`
- `evidence_found`
- `brief_section`
- `warning`
- `error`
- `done`
