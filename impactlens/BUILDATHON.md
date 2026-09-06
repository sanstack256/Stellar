# ImpactLens

## One-sentence summary
Graph-verified change-impact analysis that combines Entire structural evidence and checkpoint intent with Databricks retrieval and AI reasoning.

## Problem, intended user and why it matters
Developers need a verifiable way to understand the blast radius of a code change, select focused tests, and identify risks that are easy to miss from a Git diff alone.

## Selected Entire track and why Entire is essential
**Track 2 — Build with Graph Intelligence.** Entire Graph is the structural evidence source for affected relationships, while Entire Checkpoints preserve the intent and decisions that explain why the change exists. Without those two inputs, the product loses the evidence needed to make and verify its recommendation.

## Architecture and main workflow
Git commit → Entire Graph + Entire Checkpoint → Databricks Lakehouse → Databricks AI Search → deterministic impact/risk/test analysis → configured model-serving endpoint → evidence-backed report.

## Entire Graph findings and verification
**To be completed during the build:** record one search/definition lookup, one impact analysis before the high-risk change, and the final semantic diff. For each finding, record the source/test verification.

## Noon Curveball: what changed and how we adapted
**Official constraint:** [FILL AFTER 12:00 PM — DO NOT INVENT]

**Affected behavior:** [FILL]

**Graph impact evidence before editing:** [FILL]

**Checkpoint context used to reconstruct intent:** [FILL]

**Implementation/test result:** [FILL]

## Checkpoint links and what each checkpoint proves
- Initial architecture checkpoint: [LINK]
- Pre-noon stable checkpoint: [LINK]
- Curveball response checkpoint: [LINK]
- Final verification checkpoint: [LINK]

## Setup, run and test instructions
See `README.md` and `docs/entire-workflow.md`. Keep all credentials in the environment; never commit secrets.

## Databricks use, data sources and limitations
Databricks is used for the core evidence workflow: Delta-backed storage of graph/change/checkpoint/test evidence, AI Search over the unified evidence corpus, and the configured model/evaluation path where available. Data originates from the selected Git repository, Entire Graph and Entire Checkpoints. Any synthetic or cached evidence used for fallback must be explicitly labeled in the demo.

## Known limitations and next steps
Entire Graph is static analysis and can miss dynamic dispatch/reflection/generated behavior; those cases must be disclosed and verified against source/tests. Databricks Free Edition has quota and availability constraints, so the final demo keeps a local fallback recording.
