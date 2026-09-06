from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from integrations.entire import (
    checkpoint_for_commit,
    graph_snapshot,
    impact,
    snapshot_entities,
)


class PipelineError(RuntimeError):
    pass


def _git(repo: str, args: list[str], timeout: int = 30) -> str:
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise PipelineError((p.stderr or p.stdout or "git command failed").strip())
    return p.stdout


def changed_files(repo: str, commit: str) -> list[str]:
    return [x for x in _git(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", commit]).splitlines() if x]


def changed_ranges(repo: str, commit: str) -> dict[str, list[tuple[int, int]]]:
    # Unified diff is only used to locate changed lines; semantic relationships
    # and impact come from Entire Graph.
    text = _git(repo, ["show", "--format=", "--unified=0", commit])
    result: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if current and line.startswith("@@"):
            import re
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1)); count = int(m.group(2) or "1")
                result.setdefault(current, []).append((start, start + max(count, 1) - 1))
    return result


def commit_meta(repo: str, commit: str) -> dict[str, str]:
    out = _git(repo, ["show", "-s", "--format=%H%n%an%n%aI%n%s", commit])
    parts = out.splitlines()
    return {"sha": parts[0] if parts else commit, "author": parts[1] if len(parts)>1 else "", "date": parts[2] if len(parts)>2 else "", "subject": parts[3] if len(parts)>3 else ""}


def _changed_entities(repo: str, commit: str) -> list[str]:
    entities = snapshot_entities(repo)
    ranges = changed_ranges(repo, commit)
    matches: list[tuple[int, str]] = []
    for e in entities:
        efile = e.get("file", "")
        eline = int(e.get("line") or 0)
        eend = int(e.get("end_line") or eline)
        if eline == 0 and eend == 0:
            continue
        for start, end in ranges.get(efile, []):
            if eline <= end and start <= eend:
                # Prefer the most specific entity by smallest span
                span = max(1, eend - eline)
                matches.append((span, e["entity_id"]))
                break
    if matches:
        return list(dict.fromkeys(x[1] for x in sorted(matches)))

    # If a semantic entity cannot be mapped to the hunk, query Entire Graph
    # using changed file names. This keeps the result evidence-backed rather
    # than inventing symbol names.
    result: list[str] = []
    for path in changed_files(repo, commit):
        try:
            from integrations.entire import search
            hits = search(repo, path, limit=5)
            for hit in hits:
                eid = hit.get("entity_id") or hit.get("symbol") or hit.get("name")
                if eid: result.append(str(eid))
        except Exception:
            continue
    return list(dict.fromkeys(result))


def recent_checkpoints(repo: str, head: str, limit: int = 12) -> list[dict[str, Any]]:
    commits = [x for x in _git(repo, ["log", f"-{max(1, min(limit, 30))}", "--format=%H"]).splitlines() if x]
    out=[]
    for sha in commits:
        if sha == head:
            continue
        try:
            out.append(checkpoint_for_commit(repo, sha))
        except Exception:
            continue
    return out


def build(repo: str, commit: str, repo_name: str | None = None) -> dict[str, Any]:
    files = changed_files(repo, commit)
    meta = commit_meta(repo, commit)
    entities = _changed_entities(repo, commit)
    if not entities and files:
        # File-level evidence is explicit, not a fabricated symbol.
        entities = [f"file:{f}" for f in files]

    graph_evidence: list[dict[str, Any]] = []
    all_affected: dict[str, dict[str, Any]] = {}
    queue: list[tuple[str, int]] = [(e, 1) for e in entities]
    visited = set(entities)

    while queue:
        curr_entity, depth = queue.pop(0)
        evidence = impact(repo, curr_entity)
        graph_evidence.append(evidence)
        for item in evidence.get("callers", []):
            eid = item.get("entity_id")
            if not eid:
                continue
            candidate = {"depth": depth, "changed_entity": curr_entity, "source": "entire_graph", "relationship": "callers", "file": item.get("file"), "line": item.get("line")}
            if eid not in all_affected or depth < all_affected[eid].get("depth", 999):
                all_affected[eid] = candidate
            if eid not in visited and depth < 3:
                visited.add(eid)
                queue.append((eid, depth + 1))

    checkpoint=checkpoint_for_commit(repo, commit)
    historical=recent_checkpoints(repo, commit)
    snapshot=graph_snapshot(repo)
    return {
        "repo": repo_name or Path(repo).name,
        "repo_path": str(Path(repo).resolve()),
        "commit": commit,
        "commit_meta": meta,
        "changed_files": files,
        "changed_entities": entities,
        "all_affected": all_affected,
        "graph_evidence": graph_evidence,
        "graph_snapshot": snapshot,
        "checkpoint": checkpoint,
        "historical_checkpoints": historical,
    }
