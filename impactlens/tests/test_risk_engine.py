"""
Unit tests for risk_engine.scorer.

These pin down the behavior a risk engine actually needs to be trustworthy:
monotonicity (more blast radius / less coverage / more history => higher
score, never lower), sane band boundaries, and no crashes on edge-case
(empty) input.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk_engine.scorer import score_change

CHECKPOINT_WITH_INTENT = {"prompt": "fix the thing", "agent_reasoning": "because reasons"}
CHECKPOINT_NO_INTENT = {"prompt": None, "agent_reasoning": ""}


def _affected(n, module="payments"):
    return {f"{module}.mod.fn{i}": {"depth": 1 if i < 2 else 2} for i in range(n)}


def test_no_impact_scores_low():
    result = score_change(
        changed_entities=["utils.helpers.format_date"],
        all_affected={},
        covered_entities=set(),
        historical_matches=[],
        checkpoint=CHECKPOINT_WITH_INTENT,
    )
    assert result["risk_score"] < 40
    assert result["risk_band"] in ("LOW", "MEDIUM")


def test_large_blast_radius_in_critical_module_scores_high():
    affected = _affected(8, module="payments")
    result = score_change(
        changed_entities=["payments.service.PaymentService.validate"],
        all_affected=affected,
        covered_entities=set(),  # nothing covered
        historical_matches=[{"commit_id": "h1"}, {"commit_id": "h2"}],
        checkpoint=CHECKPOINT_NO_INTENT,
    )
    assert result["risk_band"] in ("HIGH", "CRITICAL")


def test_full_coverage_lowers_score_vs_no_coverage():
    affected = _affected(5, module="payments")
    checkpoint = CHECKPOINT_WITH_INTENT
    uncovered = score_change(
        changed_entities=["payments.service.X"], all_affected=affected,
        covered_entities=set(), historical_matches=[], checkpoint=checkpoint,
    )
    covered = score_change(
        changed_entities=["payments.service.X"], all_affected=affected,
        covered_entities=set(affected.keys()), historical_matches=[], checkpoint=checkpoint,
    )
    assert covered["risk_score"] < uncovered["risk_score"]


def test_missing_developer_intent_raises_score():
    affected = _affected(3, module="payments")
    with_intent = score_change(
        changed_entities=["payments.x"], all_affected=affected,
        covered_entities=set(affected.keys()), historical_matches=[], checkpoint=CHECKPOINT_WITH_INTENT,
    )
    without_intent = score_change(
        changed_entities=["payments.x"], all_affected=affected,
        covered_entities=set(affected.keys()), historical_matches=[], checkpoint=CHECKPOINT_NO_INTENT,
    )
    assert without_intent["risk_score"] > with_intent["risk_score"]


def test_non_critical_module_scores_lower_than_critical_for_same_shape():
    affected_critical = _affected(4, module="payments")
    affected_noncritical = _affected(4, module="analytics")
    critical = score_change(
        changed_entities=["payments.x"], all_affected=affected_critical,
        covered_entities=set(), historical_matches=[], checkpoint=CHECKPOINT_WITH_INTENT,
    )
    noncritical = score_change(
        changed_entities=["analytics.x"], all_affected=affected_noncritical,
        covered_entities=set(), historical_matches=[], checkpoint=CHECKPOINT_WITH_INTENT,
    )
    assert critical["risk_score"] > noncritical["risk_score"]


def test_score_is_always_bounded_and_labeled():
    for n in (0, 1, 5, 20, 100):
        result = score_change(
            changed_entities=["m.x"], all_affected=_affected(n),
            covered_entities=set(), historical_matches=[{"commit_id": str(i)} for i in range(n)],
            checkpoint=CHECKPOINT_NO_INTENT,
        )
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_band"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_band_boundaries_match_documented_thresholds():
    from risk_engine.scorer import _band
    assert _band(0) == "LOW"
    assert _band(30) == "LOW"
    assert _band(30.1) == "MEDIUM"
    assert _band(60) == "MEDIUM"
    assert _band(60.1) == "HIGH"
    assert _band(80) == "HIGH"
    assert _band(80.1) == "CRITICAL"
    assert _band(100) == "CRITICAL"
