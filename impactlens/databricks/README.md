# ImpactLens Databricks production path

The target production path is:

**Entire Graph + Entire Checkpoints → Delta Lake → unified AI Search → deterministic risk → Databricks Model Serving → MLflow 3 evaluation/tracing.**

## Tables

- `bronze_raw_events`: immutable-ish raw graph/checkpoint/git payloads
- `silver_code_entities`: code symbols
- `silver_code_relationships`: dependency edges
- `silver_code_changes`: changed files/entities
- `silver_checkpoints`: developer intent/history
- `silver_tests`: test inventory
- `gold_change_impact`: blast radius
- `gold_risk_scores`: explainable risk features/score
- `gold_test_recommendations`: ranked tests
- `gold_missed_risks`: missed-risk candidates
- `knowledge_documents`: unified retrieval corpus for AI Search
- `analysis_runs`: provenance and model/data-plane metadata

## Provision

```bash
python scripts/bootstrap_databricks.py
```

Create a Delta Sync AI Search index over `knowledge_documents` using a Databricks-managed embedding endpoint (for example `databricks-gte-large-en`) and set:

```bash
DATABRICKS_AI_SEARCH_ENDPOINT=...
DATABRICKS_AI_SEARCH_INDEX=main.impactlens.impactlens_knowledge
```

Databricks AI Search supports Delta Sync indexes and hybrid/semantic/full-text retrieval; the unified corpus lets ImpactLens retrieve code, tests, impact paths and historical checkpoints together.

## LLM

Set `DATABRICKS_LLM_ENABLED=true` and point `DATABRICKS_LLM_ENDPOINT` to a model-serving endpoint. The application uses the OpenAI-compatible Databricks serving interface.

## MLflow

Set `MLFLOW_ENABLED=true` when running under Managed MLflow 3. ImpactLens traces the analysis so retrieval, reasoning and output quality can be evaluated and monitored.
