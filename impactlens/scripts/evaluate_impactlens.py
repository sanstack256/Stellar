#!/usr/bin/env python3
"""Evaluate ImpactLens with MLflow 3 when Databricks Managed MLflow is available.

The dataset schema is intentionally simple so teams can add historical PRs later.
"""
from __future__ import annotations
import os, json
from pathlib import Path

CASES=[
 {"input":"Fix fraud validation for 3DS payments","expected_band":"MEDIUM","must_mention":["webhook","PaymentService"]},
 {"input":"Add order receipt email notifications","expected_band":"LOW","must_mention":["receipt"]},
 {"input":"quick fix for refund edge case","expected_band":"HIGH","must_mention":["refund","payment"]},
]

def predict(case):
    # Evaluation adapter: invoke the deployed API in CI/notebook mode.
    import requests
    base=os.environ["IMPACTLENS_URL"].rstrip("/")
    return requests.post(base+"/analyze/HEAD",json={"repo_path":os.getenv("IMPACTLENS_REPO","sample_repo"),"repo_name":"ecommerce-demo"},timeout=120).json()

def main():
    import mlflow
    from mlflow.genai.scorers import RelevanceToQuery, RetrievalGroundedness
    dataset=[{"inputs":{"query":c["input"]},"expectations":{"expected_band":c["expected_band"],"must_mention":c["must_mention"]}} for c in CASES]
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT","/Shared/ImpactLens"))
    def fn(inputs): return predict(inputs)
    result=mlflow.genai.evaluate(data=dataset,scorers=[RelevanceToQuery(),RetrievalGroundedness()],predict_fn=fn)
    print(result)
if __name__=="__main__": main()
