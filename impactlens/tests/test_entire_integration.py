"""Evidence-integrity tests for the Entire CLI integration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations import entire

ROOT = Path(__file__).resolve().parents[2]


def test_checkpoint_for_commit_marks_entire_cli_evidence_verified(monkeypatch):
    monkeypatch.setattr(entire, "_run", lambda repo, args: '{"prompt":"real intent"}')

    checkpoint = entire.checkpoint_for_commit("/repo", "abc123")

    assert checkpoint["prompt"] == "real intent"
    assert checkpoint["commit_id"] == "abc123"
    assert checkpoint["evidence_source"] == "entire_cli"
    assert checkpoint["verification_state"] == "verified"


def test_checkpoint_for_commit_never_substitutes_simulated_data(monkeypatch):
    def unavailable(repo, args):
        raise RuntimeError("entire explain unavailable")

    monkeypatch.setattr(entire, "_run", unavailable)

    checkpoint = entire.checkpoint_for_commit("/repo", "abc123")

    assert checkpoint["commit_id"] == "abc123"
    assert checkpoint["evidence_source"] == "entire_cli"
    assert checkpoint["verification_state"] == "partial"
    assert checkpoint["unavailable_reason"] == "entire explain unavailable"
    assert checkpoint["prompt"] == ""
    assert checkpoint["agent_reasoning"] == ""
    assert checkpoint["checkpoint_summary"] == "Entire checkpoint evidence is unavailable."


def test_bundled_parse_error_fixture_requires_graph_verification():
    """Use the tracked malformed TypeScript fixture, never simulated Entire output."""
    snapshot = entire.graph_snapshot(str(ROOT))
    quality = snapshot["evidence_quality"]

    assert quality["state"] == "partial"
    assert quality["verification_required"] is True
    assert "Inspect the changed source" in quality["verification_path"]
    assert any(
        failure.get("file_path") == "impactlens/repos/trading-desk-sentinel-86e59478/ui/src/App.tsx"
        for failure in quality["partial_failures"]
    )


def test_semantic_diff_marks_real_parse_fixture_as_partial():
    diff = entire.semantic_diff(str(ROOT), "HEAD~1", "HEAD")

    assert isinstance(diff["parsed"], dict)
    assert diff["dependent_count_evidence"] == "heuristic"
    assert diff["evidence_quality"]["state"] == "partial"
    assert diff["evidence_quality"]["verification_required"] is True
