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
Entire Checkpoints ───────── developer intent/history
   │
   ▼
Databricks Lakehouse / Unity Catalog
   ├── Bronze: raw evidence
   ├── Silver: code graph, changes, tests, checkpoints
   └── Gold: impact, risk, test recommendations, missed risks
   │
   ├──────────────► Databricks AI Search / TF-IDF Vector Index
   │                  unified code/history retrieval
   │
   ├──────────────► deterministic risk/features
   │
   └──────────────► Model Serving / Evidence Reasoner
                         │
                         ▼
                     Stellar Agent
                         │
                         ▼
                   MLflow 3 trace/eval
                         │
                         ▼
                     Dashboard
```

The important design choice is that the LLM **does not invent the risk score**. Structural evidence comes from Entire/AST graph, historical/contextual retrieval comes from Databricks/Search memory, and the deterministic risk engine computes an auditable score before the model explains it.

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
export DATABRICKS_SCHEMA="stellar"
export DATABRICKS_WORKSPACE_URL="https://<workspace>.cloud.databricks.com"
export DATABRICKS_AI_SEARCH_ENDPOINT="..."
export DATABRICKS_AI_SEARCH_INDEX="main.stellar.stellar_knowledge"
export DATABRICKS_LLM_ENABLED=true
export DATABRICKS_LLM_ENDPOINT="<model-serving-endpoint>"
export MLFLOW_ENABLED=true
```

Then:

```bash
python scripts/bootstrap_databricks.py
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

## Demo narrative

Use the seeded refund/payment changes in `sample_repo`. The dashboard visibly shows:

- risk score and 7-dimension component evidence,
- dependency depth and blast radius visualizer,
- ranked tests rather than the entire test suite,
- historical incident memory evidence,
- missed-risk candidates,
- data/retrieval/LLM provenance.

## Analyze a real repository

Stellar is not limited to `sample_repo`. The dashboard can import a real Git repository through `POST /repos/clone` and then analyze any commit/ref available in that clone. For public repositories, paste an HTTPS Git URL in the dashboard. For private HTTPS repositories, set `GIT_TOKEN` in the backend environment rather than embedding credentials in the URL. For a repository already on the same machine, set `STELLAR_REPO_ROOT=/path/to/your/projects` and enter its relative path in the dashboard.
