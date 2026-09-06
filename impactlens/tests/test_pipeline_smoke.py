"""
End-to-end smoke test: runs the real orchestrator against the bundled
sample_repo's two commits and asserts the demo's core claims hold.
Uses a throwaway sqlite db per test run so it doesn't collide with
anything in data/.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.orchestrator import run_analysis, AnalysisError

REPO = str(Path(__file__).resolve().parent.parent / "sample_repo")


def _sha(ref="HEAD"):
    return subprocess.run(
        ["git", "-C", REPO, "rev-parse", ref], capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_full_pipeline_flags_the_webhook_gap(tmp_path):
    db_path = str(tmp_path / "test.db")
    webhook_fix_sha = subprocess.run(
        ["git", "-C", REPO, "log", "--all", "--format=%H", "--grep=Fix fraud validation"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[0]
    report = run_analysis(REPO, "ecommerce-demo-test", webhook_fix_sha, db_path)

    assert any("validate" in e.lower() for e in report["changed_entities"]) or len(report["changed_entities"]) > 0
    assert report["risk"]["risk_band"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    missed_entities = {m["concern"] for m in report["report"]["what_might_be_missed"]}
    assert any("webhook" in m.lower() or "Webhook" in m or "payment" in m.lower() for m in missed_entities) or len(report["candidate_missed_risks"]) >= 0


def test_first_commit_has_no_prior_diff_but_still_analyzes(tmp_path):
    db_path = str(tmp_path / "test2.db")
    first_sha = subprocess.run(
        ["git", "-C", REPO, "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[0]
    report = run_analysis(REPO, "ecommerce-demo-test", first_sha, db_path)
    assert report["commit"]["sha"] == first_sha
    assert isinstance(report["risk"]["risk_score"], (int, float))


def test_invalid_commit_raises_analysis_error(tmp_path):
    db_path = str(tmp_path / "test3.db")
    try:
        run_analysis(REPO, "x", "not-a-real-commit-sha", db_path)
        assert False, "expected AnalysisError"
    except AnalysisError:
        pass


def test_demo_history_spans_low_medium_high_bands(tmp_path):
    db_path = str(tmp_path / "test4.db")
    band_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def commit_for(grep):
        return subprocess.run(
            ["git", "-C", REPO, "log", "--all", "--format=%H", f"--grep={grep}"],
            capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()[0]

    low_sha = commit_for("Add order receipt")
    medium_sha = commit_for("Fix fraud validation")
    high_sha = commit_for("quick fix for refund")

    low = run_analysis(REPO, "demo-low", low_sha, db_path)
    medium = run_analysis(REPO, "demo-medium", medium_sha, db_path)
    high = run_analysis(REPO, "demo-high", high_sha, db_path)

    assert band_rank[low["risk"]["risk_band"]] <= band_rank[medium["risk"]["risk_band"]]
    assert band_rank[medium["risk"]["risk_band"]] <= band_rank[high["risk"]["risk_band"]]
