from __future__ import annotations
import logging
import os
import uuid
from pathlib import Path

from engine.entire_pipeline import build, PipelineError
from engine.test_inventory import inventory, rank
from risk_engine.scorer import score_change
from llm_agent.agent import analyze as llm_analyze
from integrations.databricks import enabled as databricks_enabled, DatabricksStore, AISearchStore
from integrations.entire import semantic_diff

logger = logging.getLogger("stellar")


class AnalysisError(Exception):
    pass


def _trace_analysis(context):
    if os.getenv("MLFLOW_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        return llm_analyze(context)
    try:
        import mlflow
        if hasattr(mlflow, "trace"):
            @mlflow.trace(name="stellar.analysis", span_type="AGENT")
            def traced():
                return llm_analyze(context)
            return traced()
    except Exception as exc:
        logger.warning("MLflow tracing unavailable: %s", exc)
    return llm_analyze(context)


def _coverage(tests, affected, changed):
    covered = set()
    corpus = [(t["file"], t.get("text", "").lower()) for t in tests]
    for item in list(affected) + list(changed):
        leaf = str(item).split(".")[-1].lower()
        for _, text in corpus:
            if leaf and leaf in text:
                covered.add(item)
                break
    return covered


def _missed(affected, covered, history):
    out = []
    history_text = " ".join(str(x) for x in history).lower()
    for eid, item in affected.items():
        if eid in covered:
            continue
        terms = [t.lower() for t in str(eid).replace(".", "/").split("/") if len(t) > 2]
        evidence = sum(1 for t in terms if t in history_text)
        score = min(100, 45 + int(item.get("depth", 0)) * 12 + evidence * 15)
        out.append({
            "entity_id": eid,
            "missed_risk_score": score,
            "reason": "affected path lacks direct test evidence" + (" and has historical incident references" if evidence else ""),
            "supporting_checkpoint_id": history[0].get("commit_id") if evidence and history else None
        })
    return sorted(out, key=lambda x: -x["missed_risk_score"])[:8]


def _search_history(query, repo_name, local_history):
    if not databricks_enabled():
        return local_history
    try:
        return AISearchStore().search(query, k=8, repo=repo_name)
    except Exception as exc:
        logger.warning("Databricks AI Search unavailable; falling back to local checkpoints: %s", exc)
        return local_history


def run_analysis(repo_path, repo_name, commit, db_path=None, semantic_base=None):
    allow_fallback = os.getenv("STELLAR_ALLOW_LOCAL_FALLBACK", os.getenv("IMPACTLENS_ALLOW_LOCAL_FALLBACK", "true")).lower() in {"1", "true", "yes", "on"}
    if not databricks_enabled() and not allow_fallback:
        raise AnalysisError("Databricks is disabled. Set DATABRICKS_ENABLED=true or STELLAR_ALLOW_LOCAL_FALLBACK=true.")
    
    try:
        result = build(repo_path, commit, repo_name)
    except PipelineError as exc:
        raise AnalysisError(str(exc)) from exc
    
    tests = inventory(repo_path)
    affected = [{"entity_id": k, **v} for k, v in sorted(result["all_affected"].items(), key=lambda x: (x[1].get("depth", 0), x[0]))]
    covered = _coverage(tests, result["all_affected"], result["changed_entities"])
    recommendations = rank(tests, [a for a in affected], result["changed_entities"])
    
    history_query = " ".join([result["checkpoint"].get("prompt", "") or "", result["checkpoint"].get("checkpoint_summary", "") or "", *result["changed_entities"]])
    historical = _search_history(history_query, repo_name, result["historical_checkpoints"])
    missed = _missed(result["all_affected"], covered, historical)
    
    risk = score_change(result["changed_entities"], result["all_affected"], covered, historical, result["checkpoint"], result.get("graph_evidence"))
    
    context = {
        "repo": repo_name,
        "commit": result["commit_meta"],
        "changed_files": result["changed_files"],
        "changed_entities": result["changed_entities"],
        "affected_entities": affected,
        "developer_checkpoint": result["checkpoint"],
        "historical_checkpoints_matched": historical,
        "risk": risk,
        "recommended_tests": recommendations,
        "candidate_missed_risks": missed,
        "evidence": {"graph": result["graph_evidence"]}
    }
    
    report = _trace_analysis(context)
    run_id = str(uuid.uuid4())
    final = {
        **context,
        "report": report,
        "data_plane": "databricks" if databricks_enabled() else "local-demo",
        "run_id": run_id
    }
    
    if semantic_base:
        try:
            final["semantic_diff"] = semantic_diff(repo_path, semantic_base, commit)
        except Exception as exc:
            final["semantic_diff"] = {"error": str(exc), "base": semantic_base, "head": commit}
            
    if databricks_enabled():
        try:
            DatabricksStore().write(result, risk, tests=tests, recommended_tests=recommendations, missed=missed, run_id=run_id, llm_engine=report.get("engine", "unknown"))
            final["databricks_write"] = "ok"
        except Exception as exc:
            final["databricks_write"] = f"error: {exc}"
            
    return final
