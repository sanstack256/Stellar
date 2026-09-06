#!/usr/bin/env python3
"""Run evaluation for Stellar against sample cases or a custom dataset."""
from __future__ import annotations
import argparse
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
    return requests.post(base + "/analyze/HEAD", json={"repo_path": repo, "repo_name": "sample_repo"}, timeout=120).json()


def main():
    parser = argparse.ArgumentParser(description="Evaluate Stellar impact predictions")
    parser.add_argument("--dataset", required=False, help="Path to JSON dataset")
    args = parser.parse_args()

    if args.dataset:
        with open(args.dataset, encoding="utf-8") as f:
            dataset_cases = json.load(f)
        print(f"Loaded {len(dataset_cases)} evaluation cases from {args.dataset}.")
        dataset = [{"inputs": {"query": c.get("input", "")}, "expectations": c} for c in dataset_cases]
    else:
        dataset = [{"inputs": {"query": c["input"]}, "expectations": {"expected_band": c["expected_band"], "must_mention": c["must_mention"]}} for c in CASES]

    try:
        import mlflow
        from mlflow.genai.scorers import RelevanceToQuery, RetrievalGroundedness
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "/Shared/Stellar"))
        result = mlflow.genai.evaluate(data=dataset, scorers=[RelevanceToQuery(), RetrievalGroundedness()], predict_fn=predict)
        print(result)
    except Exception as exc:
        print(f"Local test run without MLflow tracking: {exc}")
        for item in dataset:
            print("Running test case:", item["inputs"]["query"])
            res = predict(item["inputs"]["query"])
            print("Result band:", res.get("risk_band"), "score:", res.get("risk_score"))


if __name__ == "__main__":
    main()
