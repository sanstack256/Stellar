"""Repository-agnostic smoke tests for the real ImpactLens pipeline."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.orchestrator import AnalysisError, run_analysis
from engine.entire_pipeline import build
from llm_agent import agent as llm_agent

REPO = str(Path(__file__).resolve().parent.parent / "sample_repo")


def _sha(ref="HEAD"):
    return subprocess.run(
        ["git", "-C", REPO, "rev-parse", ref], capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_current_commit_builds_real_entire_evidence():
    commit = _sha()

    result = build(REPO, commit, "repository-under-test")

    assert result["commit_meta"]["sha"] == commit
    assert isinstance(result["changed_files"], list)
    assert isinstance(result["changed_entities"], list)
    assert isinstance(result["graph_evidence"], list)
    assert result["checkpoint"]["evidence_source"] == "entire_cli"
    assert result["checkpoint"]["verification_state"] in {"verified", "partial"}


def test_first_commit_has_no_parent_diff_but_builds_evidence_without_llm():
    first_sha = subprocess.run(
        ["git", "-C", REPO, "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[0]
    result = build(REPO, first_sha, "repository-under-test")

    assert result["commit_meta"]["sha"] == first_sha
    assert result["changed_files"] == []
    assert result["changed_entities"] == []
    assert result["all_affected"] == {}


def test_invalid_commit_raises_analysis_error(tmp_path):
    db_path = str(tmp_path / "test3.db")
    try:
        run_analysis(REPO, "repository-under-test", "not-a-real-commit-sha", db_path)
        assert False, "expected AnalysisError"
    except AnalysisError:
        pass


def test_llm_base_url_is_an_explicit_production_contract(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="LLM_BASE_URL is required"):
        llm_agent._required("LLM_BASE_URL")
