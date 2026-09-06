"""Unit tests for entire_sim.graph_builder against the bundled sample_repo."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from entire_sim import graph_builder

REPO = str(Path(__file__).resolve().parent.parent / "sample_repo")


def test_build_graph_finds_known_entities():
    graph = graph_builder.build_graph(REPO)
    assert "payments.service.PaymentService.validate" in graph.entities
    assert "webhooks.processor.WebhookProcessor.retry" in graph.entities
    assert "checkout.controller.CheckoutController.checkout" in graph.entities


def test_impact_blast_radius_includes_transitive_callers():
    graph = graph_builder.build_graph(REPO)
    impact = graph.impact("payments.service.PaymentService.validate")
    affected_ids = {a["entity_id"] for a in impact["affected_entities"]}
    # webhooks.processor.WebhookProcessor.handle_payment_webhook calls validate() directly
    assert "webhooks.processor.WebhookProcessor.handle_payment_webhook" in affected_ids
    # .retry() calls handle_payment_webhook(), so it's a transitive (depth 2) dependent
    assert "webhooks.processor.WebhookProcessor.retry" in affected_ids


def test_impact_on_leaf_function_has_no_callers():
    graph = graph_builder.build_graph(REPO)
    # retry() is a leaf in the caller graph: it calls things, but nothing
    # in the sample repo calls it, so its blast radius should be empty.
    impact = graph.impact("webhooks.processor.WebhookProcessor.retry")
    assert impact["affected_entities"] == []


def test_malformed_python_file_does_not_crash_build(tmp_path):
    (tmp_path / "broken.py").write_text("def f(:\n  this is not valid python")
    (tmp_path / "fine.py").write_text("def g():\n    return 1\n")
    graph = graph_builder.build_graph(str(tmp_path))
    assert "fine.g" in graph.entities
    assert not any("broken" in e for e in graph.entities)


def test_entities_touched_by_diff_prefers_method_over_class():
    ranges = {"payments/service.py": [(14, 16)]}  # inside validate()'s body (def at line 12)
    touched = graph_builder.entities_touched_by_diff(REPO, ["payments/service.py"], ranges)
    assert "payments.service.PaymentService.validate" in touched
    assert "payments.service.PaymentService" not in touched
