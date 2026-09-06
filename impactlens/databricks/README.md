# Databricks data plane

## Why Databricks is essential
Databricks is not an archive for a finished report. It is the product's evidence memory: raw Entire/Git/checkpoint events are normalized into Delta tables, the unified corpus is indexed for AI Search, and the resulting evidence is used during impact analysis.

## Data layers
- Bronze: raw evidence with provenance.
- Silver: entities, relationships, changes, checkpoints and tests.
- Gold: impact paths, risk features, test recommendations, missed risks and analysis runs.
- Knowledge corpus: retrieval documents linking each recommendation to evidence.

## Provisioning
Use the configured Databricks workspace, catalog and schema from the environment. Do not copy workspace URLs, tokens, index names or model endpoints into source.

The Free Edition guide calls for one final shared workspace and a narrow deployed slice. This project uses a single SQL warehouse for the application data path and avoids any hardcoded cluster requirement.

## AI Search
Create a Delta Sync index over the configured knowledge table and set its endpoint/index names through environment variables. The application never assumes a particular catalog, schema, index or embedding endpoint.

## Model
Use the model-serving endpoint available in the final workspace. Its base URL, credentials and model name are environment configuration.

## Evidence
Record the workspace/app/endpoint URL, reproduction steps and data provenance in the final submission without exposing credentials.
