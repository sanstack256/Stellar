"""Entire Graph + Checkpoint integration used by the Buildathon product.

There is deliberately no synthetic graph/checkpoint provider in the product
path. If Entire is not installed or activated, the analysis fails clearly.
"""
from __future__ import annotations
import json, os, re, subprocess
from typing import Any


def _run(repo: str, args: list[str], timeout: int = 120) -> str:
    p=subprocess.run(["entire", *args], cwd=repo, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "entire command failed").strip())
    return p.stdout


def verify(repo: str) -> dict[str, Any]:
    version=_run(repo,["graph","version"]).strip()
    capabilities=None
    try: capabilities=_extract_json(_run(repo,["graph","capabilities","--json"]))
    except Exception: pass
    return {"available":True,"version":version,"capabilities":capabilities}


def _extract_json(text: str) -> Any:
    text=text.strip()
    try: return json.loads(text)
    except json.JSONDecodeError: pass
    starts=[i for i in (text.find("{"),text.find("[")) if i>=0]
    if not starts: return None
    start=min(starts)
    for end in range(len(text),start,-1):
        try: return json.loads(text[start:end])
        except json.JSONDecodeError: continue
    return None


def graph_snapshot(repo: str) -> dict[str, Any]:
    raw=_run(repo,["graph","snapshot","--repo","."])
    rows=[]
    for line in raw.splitlines():
        obj=_extract_json(line)
        if isinstance(obj,dict): rows.append(obj)
    return {"raw":raw,"rows":rows}


def _location(obj: dict[str, Any]):
    file=obj.get("file") or obj.get("path") or obj.get("file_path")
    line=obj.get("line") or obj.get("start_line")
    loc=obj.get("location")
    if isinstance(loc,dict):
        file=file or loc.get("file") or loc.get("path")
        line=line or loc.get("line") or loc.get("start_line")
    return (str(file) if file else None, int(line) if str(line).isdigit() else None)


def snapshot_entities(repo: str) -> list[dict[str, Any]]:
    rows=graph_snapshot(repo)["rows"]
    out=[]
    for row in rows:
        eid=row.get("entity_id") or row.get("id") or row.get("qualified_name") or row.get("name")
        file,line=_location(row)
        if eid and file:
            out.append({"entity_id":str(eid),"kind":str(row.get("kind") or row.get("type") or "symbol"),"file":file,"line":line or 0,"end_line":row.get("end_line") or row.get("endLine") or line or 0,"module":row.get("module") or "","signature":row.get("signature") or "","raw":row})
    return out


def search(repo: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    raw=_run(repo,["graph","search","--repo",".","--profile","full","--query",query])
    data=_extract_json(raw)
    if isinstance(data,dict):
        data=data.get("results") or data.get("hits") or data.get("data") or []
    if not isinstance(data,list): return []
    return [x for x in data[:limit] if isinstance(x,dict)]


def impact(repo: str, symbol: str) -> dict[str, Any]:
    short_sym = symbol.split(":")[-1] if ":" in symbol else symbol
    callers: list[dict[str, Any]] = []
    callees: list[dict[str, Any]] = []
    raw = ""
    try:
        raw = _run(repo, ["graph", "impact", "--repo", ".", "--symbol", short_sym])
        section = None
        for line in raw.splitlines():
            low = line.strip().lower()
            if low.startswith("callers"): section = "callers"; continue
            if low.startswith("callees"): section = "callees"; continue
            if any(low.startswith(k) for k in ("type consumers", "data flows", "co-change", "same-container")): section = None; continue
            if line.strip().startswith("-") and section and not line.strip().startswith("- none"):
                parts = line.strip()[1:].strip().split()
                if parts:
                    sym_name = parts[0]
                    file_match = re.search(r"\(([^,:]+)(?::(\d+))?", line)
                    f_name = file_match.group(1) if file_match else ""
                    l_num = int(file_match.group(2)) if (file_match and file_match.group(2)) else 0
                    item = {"entity_id": sym_name, "file": f_name, "line": l_num, "depth": 1}
                    (callers if section == "callers" else callees).append(item)
    except Exception:
        raw = ""

    # Enrich from snapshot relation records
    try:
        snap = graph_snapshot(repo)
        for row in snap.get("rows", []):
            if row.get("record_type") == "relation" and row.get("type") in ("CALLS", "CONSTRUCTS", "DATA_FLOWS"):
                to_id = str(row.get("to_id", ""))
                from_id = str(row.get("from_id", ""))
                if short_sym in to_id or symbol in to_id:
                    from_short = from_id.split(":")[-1] if ":" in from_id else from_id
                    if not any(c["entity_id"] == from_short for c in callers):
                        callers.append({"entity_id": from_short, "file": "", "line": 0, "depth": 1})
                elif short_sym in from_id or symbol in from_id:
                    to_short = to_id.split(":")[-1] if ":" in to_id else to_id
                    if not any(c["entity_id"] == to_short for c in callees):
                        callees.append({"entity_id": to_short, "file": "", "line": 0, "depth": 1})
    except Exception:
        pass

    return {"symbol": symbol, "callers": callers, "callees": callees, "raw": raw}


def checkpoint_for_commit(repo: str, commit: str) -> dict[str, Any]:
    try:
        raw=_run(repo,["explain","--commit",commit])
        data=_extract_json(raw)
        if isinstance(data,dict):
            data["raw"] = raw
            data.setdefault("commit_id", commit)
            data["evidence_source"] = "entire_cli"
            data["verification_state"] = "verified"
            return data
        return {
            "commit_id": commit,
            "raw": raw,
            "checkpoint_summary": raw[:2000],
            "agent_reasoning": raw,
            "prompt": "",
            "evidence_source": "entire_cli",
            "verification_state": "verified",
        }
    except Exception as exc:
        # Checkpoint content must come from `entire explain`; do not substitute
        # commit-message-derived simulation data when that command is unavailable.
        return {
            "commit_id": commit,
            "session_id": None,
            "prompt": "",
            "agent_reasoning": "",
            "checkpoint_summary": "Entire checkpoint evidence is unavailable.",
            "author": "",
            "timestamp": "",
            "raw": "",
            "evidence_source": "entire_cli",
            "verification_state": "partial",
            "unavailable_reason": str(exc),
        }


def semantic_diff(repo: str, base: str, head: str) -> dict[str, Any]:
    raw=_run(repo,["graph","diff","--repo",".",base,head])
    return {"base":base,"head":head,"raw":raw,"parsed":_extract_json(raw)}
