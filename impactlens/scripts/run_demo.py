from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from api.orchestrator import run_analysis

REPO_PATH = str(BASE_DIR / "sample_repo")
REPO_NAME = "ecommerce-demo"
DB_PATH = str(BASE_DIR / "data" / "stellar.db")


def main():
    commit = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    sha = subprocess.run(
        ["git", "-C", REPO_PATH, "rev-parse", commit],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    report = run_analysis(REPO_PATH, REPO_NAME, sha, DB_PATH)

    out_path = BASE_DIR / "data" / f"report_{sha[:8]}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str))

    print(json.dumps(report, indent=2, default=str))
    print(f"\nSaved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
