<<<<<<< HEAD
"""Deterministic, repository-agnostic impact scoring."""
from __future__ import annotations


def _band(score: float) -> str:
    if score <= 30: return "LOW"
    if score <= 60: return "MEDIUM"
    if score <= 80: return "HIGH"
=======
from __future__ import annotations

CRITICAL_MODULES = {"payments", "checkout", "refunds", "webhooks"}


def _band(score: float) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd
    return "CRITICAL"


def score_change(changed_entities, all_affected, covered_entities, historical_matches, checkpoint, graph=None):
<<<<<<< HEAD
    n=len(all_affected)
    direct=sum(1 for v in all_affected.values() if v.get("depth")==1)
    max_depth=max([int(v.get("depth",0)) for v in all_affected.values()] or [0])
    # Criticality is inferred only from graph evidence. Route/public/entrypoint
    # entities are more exposed; otherwise fan-in is used as the proxy.
    kinds=[]
    if graph:
        for item in graph:
            text=jsonish(item).lower()
            if any(k in text for k in ("route","endpoint","handler","entrypoint")): kinds.append(1)
    exposure=min(100, (direct/max(1,n))*100 if n else 0)
    public_surface=100 if kinds else min(100, direct*12)
    gap=(sum(e not in covered_entities for e in all_affected)/n*100) if n else 0
    history=min(len(historical_matches)/5,1)*100
    intent=0 if (checkpoint.get("prompt") or checkpoint.get("agent_reasoning")) else 100
    depth=min(max_depth/5,1)*100
    breadth=min(n/15,1)*100
    score=round(min(100, .20*exposure+.15*breadth+.15*public_surface+.18*gap+.10*history+.10*intent+.12*depth),1)
    reasons=[]
    if direct: reasons.append(f"{direct} direct graph relationship(s) were identified")
    if n: reasons.append(f"{n} affected graph entities were identified")
    if max_depth>1: reasons.append(f"impact reaches {max_depth} dependency levels")
    if public_surface>=70: reasons.append("graph evidence indicates an externally exposed or entry-point surface")
    if gap: reasons.append(f"{round(gap)}% of affected entities lack matched test evidence")
    if historical_matches: reasons.append(f"{len(historical_matches)} historical checkpoint record(s) were retrieved")
    if intent: reasons.append("checkpoint intent is unavailable or incomplete")
    return {"risk_score":score,"risk_band":_band(score),"components":{"graph_exposure":round(exposure,1),"blast_radius":round(breadth,1),"surface_criticality":round(public_surface,1),"coverage_gap":round(gap,1),"historical_evidence":round(history,1),"checkpoint_uncertainty":round(intent,1),"dependency_depth":round(depth,1)},"risk_reasons":reasons}


def jsonish(value):
    try:
        import json
        return json.dumps(value, default=str)
    except Exception:
        return str(value)
=======
    n = len(all_affected)
    direct = sum(1 for v in all_affected.values() if v.get("depth") == 1)
    max_depth = max([v.get("depth", 0) for v in all_affected.values()] or [0])
    modules = {e.split(".")[0] for e in list(changed_entities) + list(all_affected)}
    central = min(direct / 6, 1) * 100
    depend = min(n / 10, 1) * 100
    critical = 100 if modules & CRITICAL_MODULES else 20
    gap = (sum(e not in covered_entities for e in all_affected) / n * 100) if n else 0
    historical = min(len(historical_matches) / 3, 1) * 100
    uncertainty = 20 if (checkpoint.get("prompt") or checkpoint.get("agent_reasoning")) else 90
    depth_component = min(max_depth / 4, 1) * 100
    score = round(min(100, .25 * central + .18 * depend + .12 * critical + .15 * gap + .10 * historical + .08 * uncertainty + .12 * depth_component), 1)
    reasons = []
    if direct:
        reasons.append(f"{direct} direct caller(s) depend on changed code")
    if n:
        reasons.append(f"{n} downstream entities are in the blast radius")
    if max_depth >= 2:
        reasons.append(f"impact propagates {max_depth} dependency levels")
    if modules & CRITICAL_MODULES:
        reasons.append(f"critical module(s): {', '.join(sorted(modules & CRITICAL_MODULES))}")
    if gap:
        reasons.append(f"{round(gap)}% of affected entities lack direct test coverage")
    if historical_matches:
        reasons.append(f"{len(historical_matches)} relevant historical record(s) were retrieved")
    if not (checkpoint.get("prompt") or checkpoint.get("agent_reasoning")):
        reasons.append("developer intent is unclear")
    return {
        "risk_score": score,
        "risk_band": _band(score),
        "components": {
            "centrality": round(central, 1),
            "dependents": round(depend, 1),
            "criticality": round(critical, 1),
            "coverage_gap": round(gap, 1),
            "historical_frequency": round(historical, 1),
            "checkpoint_uncertainty": round(uncertainty, 1),
            "dependency_depth": round(depth_component, 1)
        },
        "risk_reasons": reasons
    }
>>>>>>> 0835bb57aebcab1729d4860c16fead27214b5ccd
