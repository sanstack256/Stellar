"""Real Entire Graph / Entire Checkpoints integration.

The adapter is deliberately evidence-preserving: the raw CLI output is kept
alongside normalized facts so the UI/LLM can distinguish graph evidence from
fallback heuristics.
"""
from __future__ import annotations
import json, os, re, subprocess
from typing import Any


def enabled() -> bool:
    return os.getenv("ENTIRE_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def _run(repo: str, args: list[str], timeout: int = 120) -> str:
    p = subprocess.run(["entire", *args], cwd=repo, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "entire command failed").strip())
    return p.stdout


def status(repo: str) -> dict[str, Any]:
    out = _run(repo, ["graph", "version"])
    capabilities = None
    try:
        capabilities = _extract_json(_run(repo, ["graph", "capabilities", "--json"]))
    except Exception:
        pass
    return {"available": True, "version": out.strip(), "capabilities": capabilities}


def _extract_json(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        return None
    start = min(starts)
    for end in range(len(text), start, -1):
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            continue
    return None


def graph_snapshot(repo: str) -> dict[str, Any]:
    raw = _run(repo, ["graph", "snapshot", "--repo", "."])
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = _extract_json(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return {"raw": raw, "rows": rows}


def _location(obj: dict[str, Any]) -> tuple[str | None, int | None]:
    file = obj.get("file") or obj.get("path") or obj.get("file_path")
    line = obj.get("line") or obj.get("start_line")
    loc = obj.get("location")
    if isinstance(loc, dict):
        file = file or loc.get("file") or loc.get("path")
        line = line or loc.get("line") or loc.get("start_line")
    return (str(file) if file else None, int(line) if str(line).isdigit() else None)


def snapshot_entities(repo: str) -> list[dict[str, Any]]:
    """Normalize symbol/entity rows from Entire's NDJSON snapshot.

    Entire's snapshot is intentionally treated as an evolving machine-readable
    contract; unknown fields are retained in ``raw`` instead of discarded.
    """
    rows = graph_snapshot(repo)["rows"]
    out = []
    for row in rows:
        kind = str(row.get("kind") or row.get("type") or row.get("entity_type") or "").lower()
        eid = row.get("entity_id") or row.get("id") or row.get("qualified_name") or row.get("name")
        file, line = _location(row)
        if not eid or not file:
            continue
        if any(x in kind for x in ("function", "method", "class", "symbol", "route", "type")) or "line" in row or "location" in row:
            out.append({"entity_id": str(eid), "kind": kind or "symbol", "file": file, "line": line or 0,
                        "module": row.get("module") or "", "signature": row.get("signature") or "", "raw": row})
    return out


def impact(repo: str, symbol: str) -> dict[str, Any]:
    raw = _run(repo, ["graph", "impact", "--repo", ".", "--symbol", symbol])
    callers, callees = [], []
    section = None
    for line in raw.splitlines():
        s = line.strip(); low = s.lower()
        if low.startswith("callers"):
            section = "callers"; continue
        if low.startswith("callees"):
            section = "callees"; continue
        m = re.search(r"-\s+(.+?)\s+\(([^:()]+):(\d+)", s)
        if m and section:
            item = {"entity_id": m.group(1).strip(), "file": m.group(2), "line": int(m.group(3))}
            (callers if section == "callers" else callees).append(item)
    return {"symbol": symbol, "callers": callers, "callees": callees, "raw": raw}


def checkpoint_for_commit(repo: str, commit: str) -> dict[str, Any]:
    """Use the current Entire CLI explain contract for a commit."""
    raw = _run(repo, ["explain", "--commit", commit])
    data = _extract_json(raw)
    if isinstance(data, dict):
        data["raw"] = raw; data.setdefault("commit_id", commit); return data
    # Text output is still useful evidence. Preserve it verbatim.
    fields: dict[str, Any] = {"commit_id": commit, "raw": raw, "checkpoint_summary": raw[:1600], "agent_reasoning": raw}
    for key, pattern in (("session_id", r"Session:\s*(\S+)"), ("author", r"Author:\s*(.+)"), ("intent", r"Intent:\s*(.+)"), ("outcome", r"Outcome:\s*(.+)")):
        m = re.search(pattern, raw)
        if m: fields[key] = m.group(1).strip()
    fields["prompt"] = fields.get("intent", "")
    return fields
