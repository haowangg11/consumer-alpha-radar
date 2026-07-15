# Consumer Alpha Radar - AI Engineering Guidelines


## Project Overview

Consumer Alpha Radar is an AI-native alternative data platform.

The goal:

Discover emerging consumer trends from internet signals and translate them into public market investment opportunities.


## Core Product Flow

Internet Consumer Data

↓

Trend Discovery

↓

Consumer Psychology Analysis

↓

Public Company Mapping

↓

Financial Analysis

↓

Investment Insight


## Architecture Rules


### Agent Layer

Agents are responsible for reasoning tasks.

Examples:

- Trend Discovery Agent
- Consumer Psychology Agent
- Company Mapping Agent
- Financial Analysis Agent
- Risk Critic Agent


Agents should NOT directly call LLM APIs.


### Model Layer

All LLM selection must go through Model Router.

Example:

Agent

↓

Model Router

↓

GPT / DeepSeek / Qwen


Never hardcode model calls inside agents.


### Service Layer

External services should be isolated.

Examples:

- LLM service
- Data retrieval service
- Database service


### Skills Layer

Tools should be implemented as reusable skills.

Examples:

- Google Trends Skill
- Reddit Skill
- Stock Data Skill


### Memory Layer

Memory should support:

- Short-term task memory
- Long-term trend memory
- User preference memory


## Coding Principles

1. Prefer modular architecture.
2. Avoid large monolithic files.
3. Use structured outputs.
4. Add comments for important design decisions.
5. Explain architectural changes before implementation.


## AI Engineering Requirements

The system should support:

- Multi-agent collaboration
- Loop engineering
- Memory management
- Model routing
- Evaluation harness