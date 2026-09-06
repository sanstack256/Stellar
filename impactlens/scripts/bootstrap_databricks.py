#!/usr/bin/env python3
"""Provision the maximum ImpactLens Databricks data plane.

Creates Unity Catalog Delta tables and a Delta Sync AI Search index over the
unified knowledge_documents corpus (checkpoints + tests + impact evidence).
"""
from __future__ import annotations
import os
from integrations.databricks import DatabricksStore

store=DatabricksStore(); store.init()
print(f"Delta tables ready: {store.catalog}.{store.schema}")
endpoint=os.getenv("DATABRICKS_AI_SEARCH_ENDPOINT")
index=os.getenv("DATABRICKS_AI_SEARCH_INDEX")
embedding=os.getenv("DATABRICKS_EMBEDDING_MODEL","databricks-gte-large-en")
source=f"{store.catalog}.{store.schema}.knowledge_documents"
if not endpoint or not index:
    print("Set DATABRICKS_AI_SEARCH_ENDPOINT and DATABRICKS_AI_SEARCH_INDEX to create the unified AI Search index.")
    raise SystemExit(0)
from databricks.ai_search.client import AISearchClient
client=AISearchClient(workspace_url=os.getenv("DATABRICKS_WORKSPACE_URL")) if os.getenv("DATABRICKS_WORKSPACE_URL") else AISearchClient()
try:
    idx=client.create_delta_sync_index(endpoint_name=endpoint,source_table_name=source,index_name=index,pipeline_type="TRIGGERED",primary_key="id",embedding_source_column="text",embedding_model_endpoint_name=embedding)
    print(f"AI Search index ready: {index}")
except Exception as exc:
    print(f"Index create/verify response: {exc}")
