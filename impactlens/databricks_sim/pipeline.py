"""
databricks_sim.pipeline
-------------------------
Bronze -> Silver -> Gold ETL, backed by SQLite for the demo.

Bronze:  raw graph/checkpoint/git payloads, exactly as ingested.
Silver:  normalized entities / relationships / changes / checkpoints / tests.
Gold:    decision-ready change_impact + risk_scores + test_recommendations
         + missed_risks, ready for the LLM agent and dashboard to consume.

To point this at real Databricks: replace `sqlite3.connect(db_path)` with
a `databricks.sql.connect(...)` connection (databricks-sql-connector) and
run the same DDL — it's written to be Delta/ANSI-SQL compatible.
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path

from databricks_sim.schema import DDL
from entire_sim import graph_builder, git_diff, checkpoint_sim
from integrations.entire import enabled as entire_enabled, impact as entire_impact, checkpoint_for_commit, snapshot_entities
from integrations.databricks import enabled as databricks_enabled, DatabricksStore


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    return conn


def ingest_bronze(conn: sqlite3.Connection, repo: str, commit: str, source: str, payload: dict):
    conn.execute(
        "INSERT INTO bronze_raw_events (source, repo, commit_id, payload_json) VALUES (?, ?, ?, ?)",
        (source, repo, commit, json.dumps(payload)),
    )


def run_pipeline(repo_path: str, repo_name: str, commit: str, db_path: str) -> dict:
    """
    Full Bronze -> Silver -> Gold run for one commit. Returns the gold-layer
    result set (also persisted to SQLite for AI Search / the API to read).
    """
    conn = get_connection(db_path)

    # ---- Extract (mirrors Entire Graph + Entire Checkpoints + git) ----
    changed_files = git_diff.get_changed_files(repo_path, commit)
    changed_ranges = git_diff.get_changed_line_ranges(repo_path, commit)
    # Entire Graph is the primary graph for real repositories/languages. The
    # local AST graph remains a deterministic offline fallback.
    graph = None
    changed_entities = []
    if entire_enabled():
        try:
            rows = snapshot_entities(repo_path)
            if rows:
                graph = graph_builder.RepoGraph()
                for x in rows:
                    graph.add_entity(graph_builder.Entity(
                        entity_id=x["entity_id"], kind=x.get("kind","symbol"),
                        file=x.get("file", ""), line=int(x.get("line") or 0),
                        module=x.get("module", ""), signature=x.get("signature", "")))
                # Best-effort relationship normalization from snapshot rows.
                for x in __import__("integrations.entire", fromlist=["graph_snapshot"]).graph_snapshot(repo_path)["rows"]:
                    src=x.get("source") or x.get("source_entity") or x.get("from")
                    dst=x.get("target") or x.get("target_entity") or x.get("to")
                    if src and dst:
                        graph.add_relationship(graph_builder.Relationship(str(src), str(dst), str(x.get("relationship") or x.get("type") or "related"), float(x.get("confidence") or 1.0)))
                for entity in graph.entities.values():
                    for start, end in changed_ranges.get(entity.file, []):
                        if start <= entity.line <= end:
                            changed_entities.append(entity.entity_id); break
        except Exception:
            graph = None
            changed_entities = []
    if graph is None:
        graph = graph_builder.build_graph(repo_path)
        changed_entities = graph_builder.entities_touched_by_diff(repo_path, changed_files, changed_ranges)
    if not changed_entities and changed_files:
        # If a real graph cannot map a changed hunk to a symbol, use a file-level
        # seed. This keeps polyglot repositories analyzable instead of silently
        # returning an empty report.
        changed_entities = [f"file:{f}" for f in changed_files[:12]]
    commit_meta = git_diff.get_commit_meta(repo_path, commit)
    if entire_enabled():
        try:
            checkpoint = checkpoint_for_commit(repo_path, commit)
        except Exception:
            checkpoint = checkpoint_sim.load_checkpoint_for_commit(repo_path, commit)
    else:
        checkpoint = checkpoint_sim.load_checkpoint_for_commit(repo_path, commit)
    historical_checkpoints = checkpoint_sim.load_historical_checkpoints()

    # ---- Bronze: land raw payloads ----
    ingest_bronze(conn, repo_name, commit, "graph", {
        "entities": [e.__dict__ for e in graph.entities.values()],
        "relationships": [r.__dict__ for r in graph.relationships],
    })
    ingest_bronze(conn, repo_name, commit, "checkpoint", checkpoint)
    ingest_bronze(conn, repo_name, commit, "git", {
        "changed_files": changed_files, "commit_meta": commit_meta,
    })

    # ---- Silver: normalize ----
    conn.execute("DELETE FROM silver_code_entities WHERE repo=? AND commit_id=?", (repo_name, commit))
    conn.execute("DELETE FROM silver_code_relationships WHERE repo=? AND commit_id=?", (repo_name, commit))
    for e in graph.entities.values():
        conn.execute(
            "INSERT INTO silver_code_entities VALUES (?,?,?,?,?,?,?,?)",
            (e.entity_id, repo_name, commit, e.kind, e.file, e.line, e.module, e.signature),
        )
    for r in graph.relationships:
        conn.execute(
            "INSERT INTO silver_code_relationships VALUES (?,?,?,?,?,?)",
            (repo_name, commit, r.source, r.target, r.relationship, r.confidence),
        )
    for f in changed_files:
        conn.execute(
            "INSERT INTO silver_code_changes VALUES (?,?,?,?,?,?,?,?)",
            (repo_name, commit, f, None, "modified", commit_meta["author"], commit_meta["date"], commit_meta["subject"]),
        )
    conn.execute(
        "INSERT INTO silver_checkpoints VALUES (?,?,?,?,?,?,?,?,0)",
        (repo_name, checkpoint["commit_id"], checkpoint["session_id"], checkpoint["prompt"],
         checkpoint["agent_reasoning"], checkpoint["checkpoint_summary"], checkpoint["author"], checkpoint["timestamp"]),
    )
    for hc in historical_checkpoints:
        conn.execute(
            "INSERT INTO silver_checkpoints VALUES (?,?,?,?,?,?,?,?,1)",
            (repo_name, hc["commit_id"], hc["session_id"], hc["prompt"],
             hc["agent_reasoning"], hc["checkpoint_summary"], hc["author"], hc["timestamp"]),
        )

    # naive test coverage index: which entity does each test file's imports touch
    conn.execute("DELETE FROM silver_tests WHERE repo=?", (repo_name,))
    test_dir = Path(repo_path) / "tests"
    for test_file in test_dir.glob("test_*.py") if test_dir.exists() else []:
        src = test_file.read_text()
        for e in graph.entities.values():
            leaf_name = e.entity_id.split(".")[-1]
            if leaf_name and f"test_{leaf_name.lower()}" in src.lower():
                pass  # explicit per-entity test naming not required; see function-name scan below
        for line in src.splitlines():
            if line.strip().startswith("def test_"):
                test_id = line.strip().split("def ")[1].split("(")[0]
                conn.execute(
                    "INSERT INTO silver_tests VALUES (?,?,?,?,?)",
                    (repo_name, test_id, str(test_file.relative_to(repo_path)), None, line.strip()),
                )

    # ---- Gold: change_impact ----
    conn.execute("DELETE FROM gold_change_impact WHERE repo=? AND commit_id=?", (repo_name, commit))
    all_affected = {}
    for changed_entity in changed_entities:
        if entire_enabled():
            try:
                real = entire_impact(repo_path, changed_entity)
                real_affected = [{"entity_id": x["entity_id"], "depth": 1} for x in real.get("callers", [])]
                # Entire Graph is the structural source of truth in real mode.
                for a in real_affected:
                    key = a["entity_id"]
                    if key not in all_affected or a["depth"] < all_affected[key]["depth"]:
                        all_affected[key] = {"depth": a["depth"], "changed_entity": changed_entity, "source": "entire_graph"}
                    conn.execute("INSERT INTO gold_change_impact VALUES (?,?,?,?,?,?)",
                                 (repo_name, commit, changed_entity, a["entity_id"], a["depth"], "entire_graph:callers"))
                continue
            except Exception:
                pass
        impact = graph.impact(changed_entity)
        for a in impact["affected_entities"]:
            key = a["entity_id"]
            if key not in all_affected or a["depth"] < all_affected[key]["depth"]:
                all_affected[key] = {"depth": a["depth"], "changed_entity": changed_entity, "source": "local_fallback"}
            conn.execute(
                "INSERT INTO gold_change_impact VALUES (?,?,?,?,?,?)",
                (repo_name, commit, changed_entity, a["entity_id"], a["depth"], "local_graph:callers"),
            )

    conn.commit()

    result = {
        "repo": repo_name,
        "commit": commit,
        "commit_meta": commit_meta,
        "changed_files": changed_files,
        "changed_entities": changed_entities,
        "all_affected": all_affected,
        "checkpoint": checkpoint,
        "historical_checkpoints": historical_checkpoints,
        "graph": graph,
    }
    if databricks_enabled():
        try:
            # Risk is computed later; persist the structural/semantic payload after return via orchestrator.
            result["databricks_enabled"] = True
        except Exception:
            result["databricks_enabled"] = False
    return result


def fetch_tests(conn: sqlite3.Connection, repo: str) -> list[dict]:
    cur = conn.execute("SELECT test_id, file, description FROM silver_tests WHERE repo=?", (repo,))
    return [{"test_id": r[0], "file": r[1], "description": r[2]} for r in cur.fetchall()]
