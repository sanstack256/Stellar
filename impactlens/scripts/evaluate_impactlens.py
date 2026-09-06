from __future__ import annotations
import os
import json
from pathlib import Path

CASES = [
    {"input": "Fix fraud validation for 3DS payments", "expected_band": "MEDIUM", "must_mention": ["webhook", "PaymentService"]},
    {"input": "Add order receipt email notifications", "expected_band": "LOW", "must_mention": ["receipt"]},
    {"input": "quick fix for refund edge case", "expected_band": "HIGH", "must_mention": ["refund", "payment"]},
]


def predict(case):
    import requests
    base = os.environ.get("STELLAR_URL", os.environ.get("IMPACTLENS_URL", "http://localhost:8000")).rstrip("/")
    repo = os.environ.get("STELLAR_REPO", os.environ.get("IMPACTLENS_REPO", "sample_repo"))
    return requests.post(base + "/analyze/HEAD", json={"repo_path": repo, "repo_name": "ecommerce-demo"}, timeout=120).json()


def main():
    import mlflow
    from mlflow.genai.scorers import RelevanceToQuery, RetrievalGroundedness
    dataset = [{"inputs": {"query": c["input"]}, "expectations": {"expected_band": c["expected_band"], "must_mention": c["must_mention"]}} for c in CASES]
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "/Shared/Stellar"))
    def fn(inputs): return predict(inputs)
    result = mlflow.genai.evaluate(data=dataset, scorers=[RelevanceToQuery(), RetrievalGroundedness()], predict_fn=fn)
    print(result)


if __name__ == "__main__":
    main()
