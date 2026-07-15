# Coding Guidelines


## Agent Design

Each agent must have:

- clear responsibility
- defined input
- structured output


## LLM Usage

No agent should directly call providers.

Use:

Agent -> Service -> Router -> Model


## Data

External data sources must be wrapped as Skills.


## Evaluation

Every AI output should be evaluated by:

- accuracy
- completeness
- confidence


## Future Requirements

Support:

- multi-agent workflows
- human feedback
- memory retrieval