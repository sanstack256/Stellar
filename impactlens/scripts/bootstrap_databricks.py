#!/usr/bin/env python3
from integrations.databricks import DatabricksStore
store=DatabricksStore(); store.init()
print("Databricks Delta schema initialized from environment configuration.")
