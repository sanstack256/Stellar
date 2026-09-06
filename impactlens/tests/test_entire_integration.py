"""Evidence-integrity tests for the Entire CLI integration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations import entire


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
