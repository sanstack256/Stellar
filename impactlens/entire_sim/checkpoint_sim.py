"""
entire_sim.checkpoint_sim
--------------------------
Stand-in for Entire Checkpoints. Real Checkpoints link a commit to the
agent session / prompt / reasoning that produced it. Here we recover the
same shape from git commit trailers (`Checkpoint-session:` / `Prompt:`
lines in the commit body) plus the free-text commit message, and merge in
a small seed file of historical checkpoints for past incidents so the
AI Search / retrieval layer has something meaningful to find.

Swap `load_checkpoint_for_commit` for a real `entire checkpoint show <sha>`
call when the Entire CLI is available.
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from entire_sim.git_diff import get_commit_message, get_commit_meta

_SESSION_RE = re.compile(r"Checkpoint-session:\s*(\S+)")
_PROMPT_RE = re.compile(r"Prompt:\s*'(.+?)'")


def load_checkpoint_for_commit(repo_path: str, commit: str) -> dict:
    message = get_commit_message(repo_path, commit)
    meta = get_commit_meta(repo_path, commit)

    session_match = _SESSION_RE.search(message)
    prompt_match = _PROMPT_RE.search(message)

    body_lines = message.splitlines()
    summary = body_lines[0] if body_lines else ""
    reasoning = "\n".join(
        l for l in body_lines[1:]
        if not l.startswith("Checkpoint-session:") and not l.startswith("Prompt:")
    ).strip()

    return {
        "commit_id": meta["sha"],
        "session_id": session_match.group(1) if session_match else None,
        "prompt": prompt_match.group(1) if prompt_match else None,
        "agent_reasoning": reasoning,
        "checkpoint_summary": summary,
        "author": meta["author"],
        "timestamp": meta["date"],
    }


def load_historical_checkpoints(seed_path: str | None = None) -> list[dict]:
    """
    Historical checkpoints from *other* past changes (bug fixes, incidents)
    that AI Search should be able to retrieve when reasoning about a new
    change. In production this table is populated continuously as Entire
    Checkpoints records every commit; for the demo we seed a few realistic
    past incidents relevant to the payment-validation change.
    """
    default = [
        {
            "commit_id": "hist_a1",
            "session_id": "sess_1a02",
            "prompt": "webhook retries are silently failing after payment validation changes",
            "agent_reasoning": (
                "A previous change to PaymentService.validate() started rejecting "
                "payments that webhook retries depend on. WebhookProcessor.retry() "
                "calls validate() on every attempt, so tightening validation broke "
                "retry success rates. Added test_webhook_retry_after_validation_change "
                "to catch this in the future."
            ),
            "checkpoint_summary": "Incident: webhook retries broken by validation change",
            "author": "past-dev",
            "timestamp": "3 months ago",
        },
        {
            "commit_id": "hist_b2",
            "session_id": "sess_2b17",
            "prompt": "refund fails silently when original payment was flagged as fraud",
            "agent_reasoning": (
                "RefundService.process_refund() assumes the payment record exists "
                "and is in an authorized state. When validate() rejects a payment, "
                "no record is saved, so refunds against that payment_id fail with a "
                "generic error. Any change to validate()'s rejection logic changes "
                "which payments are refundable."
            ),
            "checkpoint_summary": "Incident: refund failures tied to validation rejects",
            "author": "past-dev",
            "timestamp": "5 months ago",
        },
        {
            "commit_id": "hist_c3",
            "session_id": "sess_3c44",
            "prompt": "add fraud check for cross-border card mismatches",
            "agent_reasoning": (
                "Added FraudService.check() country-mismatch rule. Flagged as high "
                "risk because it changes checkout's success rate directly; rolled "
                "out behind a flag first."
            ),
            "checkpoint_summary": "Added cross-border fraud rule to FraudService",
            "author": "past-dev",
            "timestamp": "8 months ago",
        },
    ]
    if seed_path and Path(seed_path).exists():
        return json.loads(Path(seed_path).read_text())
    return default
