#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from api.orchestrator import run_analysis

p=argparse.ArgumentParser()
p.add_argument("--repo", required=True)
p.add_argument("--repo-name", required=True)
p.add_argument("--commit", required=True)
p.add_argument("--semantic-base")
a=p.parse_args()
print(json.dumps(run_analysis(a.repo,a.repo_name,a.commit,semantic_base=a.semantic_base),indent=2,default=str))
