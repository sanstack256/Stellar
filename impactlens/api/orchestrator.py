from __future__ import annotations
<<<<<<< HEAD
import logging, os, uuid
from engine.entire_pipeline import build, PipelineError
from engine.test_inventory import inventory, rank
=======
import logging
import os
import re
import uuid
from pathlib import Path

from databricks_sim import pipeline as db_pipeline
from databricks_sim.ai_search import CheckpointIndex
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd
from risk_engine.scorer import score_change
from llm_agent.agent import analyze as llm_analyze
from integrations.databricks import enabled as databricks_enabled, DatabricksStore, AISearchStore
from integrations.entire import semantic_diff

logger = logging.getLogger("stellar")


class AnalysisError(Exception):
    pass


<<<<<<< HEAD
def _trace_analysis(context):
    if os.getenv("MLFLOW_ENABLED","false").lower() not in {"1","true","yes","on"}:
        return llm_analyze(context)
    try:
        import mlflow
        if hasattr(mlflow,"trace"):
            @mlflow.trace(name="impactlens.analysis", span_type="AGENT")
            def traced():
                return llm_analyze(context)
            return traced()
    except Exception as exc:
        logger.warning("MLflow tracing unavailable: %s", exc)
    return llm_analyze(context)


def _coverage(tests, affected, changed):
    covered=set()
    corpus=[(t["file"],t.get("text","").lower()) for t in tests]
    for item in list(affected)+list(changed):
        leaf=str(item).split(".")[-1].lower()
        for _, text in corpus:
            if leaf and leaf in text: covered.add(item); break
    return covered


def _missed(affected, covered, history):
    out=[]
    history_text=" ".join(str(x) for x in history).lower()
    for eid,item in affected.items():
        if eid in covered: continue
        terms=[t.lower() for t in str(eid).replace(".","/").split("/") if len(t)>2]
        evidence=sum(1 for t in terms if t in history_text)
        score=min(100,45+int(item.get("depth",0))*12+evidence*15)
        out.append({"entity_id":eid,"missed_risk_score":score,"reason":"affected path lacks matched test evidence" + (" and has historical checkpoint references" if evidence else ""),"supporting_checkpoint_id":history[0].get("commit_id") if evidence and history else None})
    return sorted(out,key=lambda x:-x["missed_risk_score"])[:8]


def _search_history(query, repo_name, local_history):
    if not databricks_enabled():
        if os.getenv("IMPACTLENS_ALLOW_LOCAL_FALLBACK","false").lower() not in {"1","true","yes","on"}:
            raise AnalysisError("Databricks is required for the configured production path; enable it or explicitly enable the local fallback for testing")
        return local_history
    try:
        return AISearchStore().search(query,k=8,repo=repo_name)
    except Exception as exc:
        if os.getenv("IMPACTLENS_ALLOW_LOCAL_FALLBACK","false").lower() in {"1","true","yes","on"}:
            logger.warning("AI Search unavailable; explicit local fallback enabled: %s",exc)
            return local_history
        raise AnalysisError(f"Databricks AI Search unavailable: {exc}") from exc


def run_analysis(repo_path, repo_name, commit, db_path=None, semantic_base=None):
    if not databricks_enabled() and os.getenv("IMPACTLENS_ALLOW_LOCAL_FALLBACK","false").lower() not in {"1","true","yes","on"}:
        raise AnalysisError("Databricks is disabled. Set DATABRICKS_ENABLED=true for the buildathon data plane.")
    try:
        result=build(repo_path,commit,repo_name)
    except PipelineError as exc: raise AnalysisError(str(exc)) from exc
    tests=inventory(repo_path)
    affected=[{"entity_id":k,**v} for k,v in sorted(result["all_affected"].items(),key=lambda x:(x[1].get("depth",0),x[0]))]
    covered=_coverage(tests,result["all_affected"],result["changed_entities"])
    recommendations=rank(tests,[a for a in affected],result["changed_entities"])
    history_query=" ".join([result["checkpoint"].get("prompt","") or "",result["checkpoint"].get("checkpoint_summary","") or "",*result["changed_entities"]])
    historical=_search_history(history_query,repo_name,result["historical_checkpoints"])
    missed=_missed(result["all_affected"],covered,historical)
    risk=score_change(result["changed_entities"],result["all_affected"],covered,historical,result["checkpoint"],result.get("graph_evidence"))
    context={"repo":repo_name,"commit":result["commit_meta"],"changed_files":result["changed_files"],"changed_entities":result["changed_entities"],"affected_entities":affected,"developer_checkpoint":result["checkpoint"],"historical_checkpoints_matched":historical,"risk":risk,"recommended_tests":recommendations,"candidate_missed_risks":missed,"evidence":{"graph":result["graph_evidence"]}}
    report=_trace_analysis(context)
    run_id=str(uuid.uuid4())
    final={**context,"report":report,"data_plane":"databricks" if databricks_enabled() else "explicit-local-fallback","run_id":run_id}
    if semantic_base:
        try: final["semantic_diff"]=semantic_diff(repo_path,semantic_base,commit)
        except Exception as exc: final["semantic_diff"]={"error":str(exc),"base":semantic_base,"head":commit}
    if databricks_enabled():
        try:
            DatabricksStore().write(result,risk,tests=tests,recommended_tests=recommendations,missed=missed,run_id=run_id,llm_engine=report.get("engine","unknown"))
            final["databricks_write"]="ok"
        except Exception as exc:
            final["databricks_write"]="error"
            if os.getenv("IMPACTLENS_REQUIRE_DATABRICKS_WRITE","true").lower() in {"1","true","yes","on"}:
                raise AnalysisError(f"Databricks persistence failed: {exc}") from exc
=======
def _naive_test_coverage(repo_path, all_affected, changed_entities):
    tests_dir = Path(repo_path) / "tests"
    if not tests_dir.exists():
        return set()
    corpus = "\n".join(p.read_text(errors="replace") for p in tests_dir.glob("test_*.py"))
    covered = set()
    for entity_id in list(all_affected) + list(changed_entities):
        bits = entity_id.split(".")
        leaf = bits[-1]
        cls = bits[-2] if len(bits) > 1 else ""
        if cls and cls.lower() in corpus.lower() and leaf + "(" in corpus:
            covered.add(entity_id)
    return covered


def _test_recommendations(tests, affected, changed_entities, covered):
    affected_names = {a["entity_id"] for a in affected}
    tokens = set()
    for e in affected_names | set(changed_entities):
        tokens.update(x.lower() for x in re.split(r"[^A-Za-z0-9]+", e) if len(x) > 2)
    rec = []
    for t in tests:
        hay = (t.get("test_id", "") + " " + t.get("description", "") + " " + t.get("file", "")).lower()
        overlap = sum(1 for x in tokens if x in hay)
        score = min(100, overlap * 22 + (35 if any(e.split(".")[-1].lower() in hay for e in affected_names) else 0))
        if score == 0:
            score = min(100, sum(8 for x in tokens if x in hay))
        priority = "critical" if score >= 70 else "recommended" if score >= 25 else "optional"
        if score > 0:
            rec.append({
                "test_id": t["test_id"],
                "priority": priority,
                "relevance_score": round(score, 1),
                "reason": f"matched {overlap} impact-context token(s)"
            })
    return sorted(rec, key=lambda x: (-x["relevance_score"], x["test_id"]))[:10]


def _missed_risks(affected, covered, historical_matches):
    out = []
    for a in affected:
        eid = a["entity_id"]
        if eid in covered:
            continue
        hay = " ".join(str(h.get(k, "")) for h in historical_matches for k in ("agent_reasoning", "checkpoint_summary", "prompt")).lower()
        tokens = [x.lower() for x in re.split(r"[^A-Za-z0-9]+", eid) if len(x) > 2]
        evidence = sum(1 for t in tokens if t in hay)
        score = min(100, 45 + a.get("depth", 0) * 12 + evidence * 18)
        out.append({
            "entity_id": eid,
            "missed_risk_score": score,
            "reason": ("historical evidence also references this path" if evidence else "no direct test coverage found for this affected entity"),
            "supporting_checkpoint_id": historical_matches[0].get("commit_id") if evidence and historical_matches else None
        })
    return sorted(out, key=lambda x: -x["missed_risk_score"])[:8]


def _mlflow_trace(context, fn):
    if os.getenv("MLFLOW_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        return fn()
    try:
        import mlflow
        if hasattr(mlflow, "trace"):
            @mlflow.trace(name="stellar.analysis", span_type="AGENT")
            def traced():
                return fn()
            return traced()
    except Exception as exc:
        logger.warning("MLflow tracing disabled: %s", exc)
    return fn()


def run_analysis(repo_path, repo_name, commit, db_path):
    if not commit_exists(repo_path, commit):
        raise AnalysisError(f"'{commit}' is not a valid commit/ref in this repository")
    try:
        result = db_pipeline.run_pipeline(repo_path, repo_name, commit, db_path)
    except GitError as exc:
        raise AnalysisError(str(exc)) from exc

    conn = db_pipeline.get_connection(db_path)
    tests = db_pipeline.fetch_tests(conn, repo_name)
    covered = _naive_test_coverage(repo_path, result["all_affected"], result["changed_entities"])
    search_query = " ".join([result["checkpoint"].get("prompt") or "", result["checkpoint"].get("checkpoint_summary") or "", " ".join(result["changed_entities"])])
    
    if databricks_enabled():
        try:
            historical = AISearchStore().search(search_query, k=8, repo=repo_name)
        except Exception as exc:
            logger.warning("Databricks AI Search failed: %s", exc)
            historical = []
    else:
        historical = CheckpointIndex(conn, repo_name).search(search_query, k=8, historical_only=True)

    affected = [{"entity_id": k, **v} for k, v in sorted(result["all_affected"].items(), key=lambda kv: (kv[1].get("depth", 0), kv[0]))]
    recommended = _test_recommendations(tests, affected, result["changed_entities"], covered)
    missed = _missed_risks(affected, covered, historical)
    risk = score_change(result["changed_entities"], result["all_affected"], covered, historical, result["checkpoint"], result.get("graph"))
    
    conn.execute("DELETE FROM gold_risk_scores WHERE commit_id=?", (commit,))
    conn.execute("INSERT OR REPLACE INTO gold_risk_scores VALUES (?,?,?,?,?)", (repo_name, commit, risk["risk_score"], risk["risk_band"], __import__("json").dumps(risk["risk_reasons"])))
    conn.commit()

    context = {
        "repo": repo_name,
        "commit": result["commit_meta"],
        "changed_files": result["changed_files"],
        "changed_entities": result["changed_entities"],
        "affected_entities": affected,
        "developer_checkpoint": result["checkpoint"],
        "historical_checkpoints_matched": historical,
        "risk": risk,
        "recommended_tests": recommended,
        "candidate_missed_risks": missed
    }
    report = _mlflow_trace(context, lambda: llm_analyze(context))
    run_id = str(uuid.uuid4())
    final = {
        "repo": repo_name,
        "commit": result["commit_meta"],
        "changed_files": result["changed_files"],
        "changed_entities": result["changed_entities"],
        "affected_entities": affected,
        "risk": risk,
        "developer_checkpoint": result["checkpoint"],
        "historical_checkpoints_matched": historical,
        "recommended_tests": recommended,
        "candidate_missed_risks": missed,
        "report": report,
        "data_plane": "databricks" if databricks_enabled() else "local-demo",
        "run_id": run_id
    }
    if databricks_enabled():
        try:
            DatabricksStore().write(result, risk, tests=tests, recommended_tests=recommended, missed=missed, run_id=run_id, llm_engine=report.get("engine", "unknown"))
            final["databricks_write"] = "ok"
        except Exception as exc:
            final["databricks_write"] = f"error: {exc}"
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd
    return final
