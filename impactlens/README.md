<<<<<<< HEAD
# ImpactLens — Graph-Verified Change Impact

ImpactLens is a Track 2 **Build with Graph Intelligence** developer workflow. It uses **Entire Graph as structural evidence** and **Entire Checkpoints as preserved intent**, then uses Databricks to make that evidence queryable and actionable.
=======
# Stellar — AI Codebase Impact & Risk Engine

Stellar answers four engineering questions for every code change:
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd

The product answers:

<<<<<<< HEAD
1. What changed?
2. What could it affect?
3. What should we test?
4. What might we have missed?

## Non-negotiable design

There is no bundled business repository, fake graph, fake checkpoint, hardcoded risk-critical module, hardcoded Databricks workspace, or hardcoded model. The analyzed repository and commit are inputs; Entire and Databricks are configured services.

## Buildathon workflow

Follow `docs/entire-workflow.md` before running the product. The guide requires the project to be developed in the clone created through Entire's mirror workflow, checkpoints at the four milestones, graph evidence before a high-risk change, and a final semantic-diff analysis.

## Runtime path

```text
Git repository + commit
        ↓
Entire Graph
  search / snapshot / impact
        +
Entire Checkpoint
  intent / decisions / unresolved work
        ↓
Databricks Lakehouse
  raw → normalized → decision-ready
        ↓
Databricks AI Search
  historical + structural evidence retrieval
        ↓
Deterministic impact/risk engine
        ↓
Configured model-serving endpoint
        ↓
Impact report + provenance
```

## Setup
=======
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
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Populate `.env` with your actual repository workspace and Databricks/model-serving values. Never commit the file.

## Run

```bash
<<<<<<< HEAD
set -a; source .env; set +a
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

Analyze an arbitrary repository/ref from the configured workspace:

```bash
curl -X POST "$IMPACTLENS_URL/analyze/$COMMIT" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $IMPACTLENS_API_KEY" \
  -d "$(python - <<'PY'
import json,os
print(json.dumps({'repo_path':os.environ['REPO_PATH'],'repo_name':os.environ['REPO_NAME'],'semantic_base':os.getenv('SEMANTIC_BASE')}))
PY
)"
```

Use the dashboard for the same workflow.

## Databricks

The Databricks path stores raw Entire/Git/checkpoint evidence, normalized entities/relationships/tests, decision-ready impact/risk/test/missed-risk records, and a unified `knowledge_documents` corpus for AI Search. The actual catalog, schema, endpoint and model are environment configuration.

Free Edition constraints from the participant guide are respected: use one final workspace, one narrow deployed slice, avoid GPU/provisioned assumptions, and preserve a fallback screenshot/recording for fragile live steps.

## Verification

Do not treat graph output as an oracle. Verify graph findings against source and tests. The UI/API exposes evidence provenance so a judge can see which graph and checkpoint facts support the recommendation.

## Submission

See `BUILDATHON.md` for the required submission fields and the checkpoint/Curveball record. The Curveball section intentionally contains placeholders until the official constraint is revealed; it must not be invented in advance.
=======
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
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd
