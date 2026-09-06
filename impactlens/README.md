# ImpactLens — Graph-Verified Change Impact

ImpactLens is a Track 2 **Build with Graph Intelligence** developer workflow. It uses **Entire Graph as structural evidence** and **Entire Checkpoints as preserved intent**, then uses Databricks to make that evidence queryable and actionable.

The product answers:

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

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Populate `.env` with your actual repository workspace and Databricks/model-serving values. Never commit the file.

## Run

```bash
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
