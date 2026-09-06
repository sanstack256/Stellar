# Stellar — AI Codebase Impact & Risk Engine

Stellar answers four engineering questions for every code change:

1. **What changed?**
2. **What could it affect?**
3. **What should we test?**
4. **What might we have missed?**

## Architecture

```text
Git / GitHub
   │
   ▼
Entire Graph ─────────────── structural truth
   │
Entire Checkpoints ───────── developer intent / historical memory
   │
   ▼
Databricks Lakehouse / Unity Catalog
   ├── Bronze: raw evidence (graph snapshots, diffs, checkpoints)
   ├── Silver: normalized entities, relationships, changes, checkpoints, tests
   └── Gold: decision-ready impact, deterministic risk scores, test plans, missed risks
   │
   ├──────────────► Databricks AI Search / TF-IDF Vector Index
   │                  unified code/history retrieval
   │
   ├──────────────► Deterministic Risk Engine (auditable multi-factor scoring)
   │
   └──────────────► Model Serving / Evidence Reasoner
                         │
                         ▼
                     Stellar Agent
                         │
                         ▼
                   MLflow 3 Tracing & Evaluation
                         │
                         ▼
                     Dashboard
```

The core design principle is that the LLM **does not invent the risk score**. Structural evidence comes from Entire/AST graph analysis, historical/contextual retrieval comes from Databricks/Search memory, and the deterministic risk engine computes an auditable score before the model explains it.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

To run locally:
```bash
python scripts/run_demo.py HEAD
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` to access the Stellar dashboard.

## Production Databricks Configuration

Set environment variables in `.env`:

```bash
export DATABRICKS_ENABLED=true
export DATABRICKS_SERVER_HOSTNAME="..."
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/..."
export DATABRICKS_TOKEN="..."
export DATABRICKS_CATALOG="main"
export DATABRICKS_SCHEMA="stellar"
export DATABRICKS_WORKSPACE_URL="https://<workspace>.cloud.databricks.com"
export DATABRICKS_AI_SEARCH_ENDPOINT="..."
export DATABRICKS_AI_SEARCH_INDEX="main.stellar.stellar_knowledge"
export DATABRICKS_LLM_ENABLED=true
export DATABRICKS_LLM_ENDPOINT="<model-serving-endpoint>"
export MLFLOW_ENABLED=true
```

Then bootstrap Unity Catalog tables:
```bash
python scripts/bootstrap_databricks.py
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

## Entire Integration

With `entire` CLI installed, Stellar leverages Entire Graph snapshot and impact analysis as the structural source of truth across polyglot codebases, alongside Entire Checkpoints for developer intent.

## Evaluation

```bash
python scripts/evaluate_stellar.py
```

## Analyze Any Real Repository

Stellar is not limited to `sample_repo`. The dashboard can import any public or private Git repository through `POST /repos/clone` or by pasting an HTTPS Git URL into the dashboard. For private repositories, configure `GIT_TOKEN` in your environment. For local projects on disk, set `STELLAR_REPO_ROOT=/path/to/projects`.
