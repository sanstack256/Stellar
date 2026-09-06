# ImpactLens — AI Codebase Impact Engine

ImpactLens answers four engineering questions for every code change:

1. **What changed?**
2. **What could it affect?**
3. **What should we test?**
4. **What might we have missed?**

## 10/10 architecture

```text
Git / GitHub
   │
   ▼
Entire Graph ─────────────── structural truth
   │
Entire Checkpoints ───────── developer intent/history
   │
   ▼
Databricks Lakehouse / Unity Catalog
   ├── Bronze: raw evidence
   ├── Silver: code graph, changes, tests, checkpoints
   └── Gold: impact, risk, test recommendations, missed risks
   │
   ├──────────────► Databricks AI Search
   │                  unified code/history retrieval
   │
   ├──────────────► deterministic risk/features
   │
   └──────────────► Databricks Model Serving
                         │
                         ▼
                     Impact Agent
                         │
                         ▼
                   MLflow 3 trace/eval
                         │
                         ▼
                     Dashboard
```

The important design choice is that the LLM **does not invent the risk score**. Structural evidence comes from Entire, historical/contextual retrieval comes from Databricks, and the deterministic risk engine computes an auditable score before the model explains it.

## Databricks is more than storage

The real mode uses Databricks as the application's memory and AI backbone:

- Delta Lake / Unity Catalog stores normalized graph, change, checkpoint and test evidence.
- `knowledge_documents` is a unified retrieval corpus for Databricks AI Search.
- AI Search supports hybrid retrieval over current and historical evidence.
- Model Serving can supply the reasoning model.
- MLflow 3 can trace the full agent path and evaluate relevance/groundedness.
- `analysis_runs` provides provenance for every report.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_demo.py HEAD
uvicorn api.server:app --reload --port 8000
```

Open `http://localhost:8000`.

## Maximum Databricks mode

Set:

```bash
export DATABRICKS_ENABLED=true
export DATABRICKS_SERVER_HOSTNAME="..."
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/..."
export DATABRICKS_TOKEN="..."
export DATABRICKS_CATALOG="main"
export DATABRICKS_SCHEMA="impactlens"
export DATABRICKS_WORKSPACE_URL="https://<workspace>.cloud.databricks.com"
export DATABRICKS_AI_SEARCH_ENDPOINT="..."
export DATABRICKS_AI_SEARCH_INDEX="main.impactlens.impactlens_knowledge"
export DATABRICKS_LLM_ENABLED=true
export DATABRICKS_LLM_ENDPOINT="<model-serving-endpoint>"
export MLFLOW_ENABLED=true
```

Then:

```bash
python scripts/bootstrap_databricks.py
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

## Entire mode

Install Entire/Graph according to the version supported by your hackathon environment, initialize the analyzed repository, then set `ENTIRE_ENABLED=true`. The adapter preserves raw Entire output and parses callers/callees where the CLI exposes them. The local graph remains an offline fallback.

## Evaluation

```bash
python scripts/evaluate_impactlens.py
```

When `IMPACTLENS_URL` points at a deployed app and Managed MLflow 3 is configured, this evaluates the deployed analysis path using MLflow GenAI evaluation. Use a larger curated historical dataset for the final benchmark.

## Deployment

The repository includes `app.yaml` for Databricks Apps:

```bash
databricks apps deploy impactlens --source-code-path .
```

A separate static-hosted frontend is also possible, but Databricks Apps is the cleanest final demo because the FastAPI service can sit next to Unity Catalog, AI Search, Model Serving and MLflow.

## Demo narrative

Use the seeded refund/payment changes in `sample_repo`. The dashboard should visibly show:

- risk score and component evidence,
- dependency depth and blast radius,
- ranked tests rather than the entire test suite,
- historical evidence,
- missed-risk candidates,
- data/retrieval/LLM provenance.

The judge takeaway should be:

> **Entire tells us what is structurally connected. Checkpoints tell us why. Databricks remembers the history, retrieves the right evidence, evaluates the agent, and provides the AI runtime. ImpactLens turns all of that into an actionable engineering decision.**


## Analyze a real repository

ImpactLens is not limited to `sample_repo`. The dashboard can import a real Git repository through `POST /repos/clone` and then analyze any commit/ref available in that clone. For public repositories, paste an HTTPS Git URL in the dashboard. For private HTTPS repositories, set `GIT_TOKEN` in the backend environment rather than embedding credentials in the URL. For a repository already on the same machine, set `IMPACTLENS_REPO_ROOT=/path/to/your/projects` and enter its relative path in the dashboard.

With `ENTIRE_ENABLED=true`, the imported repository is analyzed with the real Entire Graph snapshot/impact commands and Entire's current `explain --commit` checkpoint interface. Entire Graph supports semantic parsing across dozens of languages and exposes search, definitions, callers/callees and impact at file/line locations. citeturn0search1

The local AST implementation remains only as a fallback for offline demos.
