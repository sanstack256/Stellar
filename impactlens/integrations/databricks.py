"""Production Databricks integration.

Databricks is treated as the intelligence backbone when enabled:
- Unity Catalog / Delta Lake stores Bronze, Silver and Gold evidence.
- A Delta Sync AI Search index retrieves historical code/change/checkpoint/test evidence.
- Optional Databricks Model Serving provides the LLM runtime.

The local SQLite/TF-IDF implementation remains available as an explicit offline fallback.
"""
from __future__ import annotations
import json, os, re
from typing import Any


def enabled() -> bool:
    return os.getenv("DATABRICKS_ENABLED", "false").lower() in {"1","true","yes","on"}

def _cfg(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)

def _ident(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value

class DatabricksStore:
    def __init__(self):
        self.server_hostname = _cfg("DATABRICKS_SERVER_HOSTNAME")
        self.http_path = _cfg("DATABRICKS_HTTP_PATH")
        self.token = _cfg("DATABRICKS_TOKEN")
        self.catalog = _ident(_cfg("DATABRICKS_CATALOG", "main") or "main")
        self.schema = _ident(_cfg("DATABRICKS_SCHEMA", "impactlens") or "impactlens")
        self._conn = None

    def connect(self):
        if self._conn:
            return self._conn
        if not all([self.server_hostname, self.http_path, self.token]):
            raise RuntimeError("Set DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH and DATABRICKS_TOKEN")
        from databricks import sql
        self._conn = sql.connect(server_hostname=self.server_hostname, http_path=self.http_path, access_token=self.token)
        return self._conn

    @property
    def prefix(self) -> str:
        return f"`{self.catalog}`.`{self.schema}`"

    def init(self):
        conn = self.connect(); cur = conn.cursor()
        p = self.prefix
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {p}")
        ddl = [
            f"""CREATE TABLE IF NOT EXISTS {p}.bronze_raw_events (event_id STRING, source STRING, repo STRING, commit_id STRING, payload_json STRING, ingested_at TIMESTAMP) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.silver_code_entities (entity_id STRING, repo STRING, commit_id STRING, kind STRING, file STRING, line INT, module STRING, signature STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.silver_code_relationships (repo STRING, commit_id STRING, source_entity STRING, target_entity STRING, relationship STRING, confidence DOUBLE) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.silver_code_changes (repo STRING, commit_id STRING, file STRING, entity_id STRING, change_type STRING, author STRING, timestamp STRING, subject STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.silver_checkpoints (repo STRING, commit_id STRING, session_id STRING, prompt STRING, agent_reasoning STRING, checkpoint_summary STRING, author STRING, timestamp STRING, is_historical BOOLEAN) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.silver_tests (repo STRING, test_id STRING, file STRING, covers_entity STRING, description STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.gold_change_impact (repo STRING, commit_id STRING, changed_entity STRING, affected_entity STRING, depth INT, relationship_path STRING, source STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.gold_risk_scores (repo STRING, commit_id STRING, risk_score DOUBLE, risk_band STRING, risk_reasons_json STRING, components_json STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.gold_test_recommendations (repo STRING, commit_id STRING, test_id STRING, priority STRING, relevance_score DOUBLE, reason STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.gold_missed_risks (repo STRING, commit_id STRING, affected_entity STRING, missed_risk_score DOUBLE, reason STRING, supporting_checkpoint_id STRING) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.knowledge_documents (id STRING, repo STRING, commit_id STRING, doc_type STRING, entity_id STRING, text STRING, metadata_json STRING, updated_at TIMESTAMP) USING DELTA""",
            f"""CREATE TABLE IF NOT EXISTS {p}.analysis_runs (run_id STRING, repo STRING, commit_id STRING, risk_score DOUBLE, risk_band STRING, llm_engine STRING, data_plane STRING, created_at TIMESTAMP) USING DELTA""",
        ]
        for statement in ddl: cur.execute(statement)
        conn.commit(); cur.close()

    def _exec(self, sql: str, params: tuple[Any, ...] = ()):
        cur = self.connect().cursor(); cur.execute(sql, params); cur.close()

    def write(self, result: dict[str, Any], risk: dict[str, Any], tests: list[dict[str, Any]] | None = None,
              recommended_tests: list[dict[str, Any]] | None = None, missed: list[dict[str, Any]] | None = None,
              run_id: str | None = None, llm_engine: str = "unknown"):
        self.init(); conn = self._conn; cur = conn.cursor(); p = self.prefix
        repo, commit = result["repo"], result["commit"]
        # Idempotent per-analysis gold layer.
        for table in ("gold_change_impact","gold_risk_scores","gold_test_recommendations","gold_missed_risks","analysis_runs"):
            cur.execute(f"DELETE FROM {p}.{table} WHERE repo=? AND commit_id=?", (repo, commit))
        for table, keycol in (("knowledge_documents","commit_id"),):
            cur.execute(f"DELETE FROM {p}.{table} WHERE repo=? AND commit_id=?", (repo, commit))

        now = "current_timestamp()"
        # Bronze payloads
        payloads = {
            "graph": {"entities":[getattr(e,'__dict__',{}) for e in result["graph"].entities.values()], "relationships":[getattr(r,'__dict__',{}) for r in result["graph"].relationships]},
            "checkpoint": result.get("checkpoint", {}),
            "git": {"changed_files":result.get("changed_files",[]),"commit_meta":result.get("commit_meta",{})},
        }
        for source, payload in payloads.items():
            cur.execute(f"INSERT INTO {p}.bronze_raw_events VALUES (?,?,?,?,?,current_timestamp())",
                        (f"{repo}:{commit}:{source}", source, repo, commit, json.dumps(payload, default=str)))

        # Silver entities/edges/changes/checkpoints/tests.
        for e in result["graph"].entities.values():
            cur.execute(f"DELETE FROM {p}.silver_code_entities WHERE repo=? AND commit_id=? AND entity_id=?", (repo,commit,e.entity_id))
            cur.execute(f"INSERT INTO {p}.silver_code_entities VALUES (?,?,?,?,?,?,?,?)",
                        (e.entity_id,repo,commit,e.kind,e.file,e.line,e.module,e.signature))
        for r in result["graph"].relationships:
            cur.execute(f"INSERT INTO {p}.silver_code_relationships VALUES (?,?,?,?,?,?)",
                        (repo,commit,r.source,r.target,r.relationship,r.confidence))
        meta = result["commit_meta"]
        for f in result.get("changed_files",[]):
            cur.execute(f"INSERT INTO {p}.silver_code_changes VALUES (?,?,?,?,?,?,?,?)",
                        (repo,commit,f,None,"modified",meta.get("author"),meta.get("date"),meta.get("subject")))
        all_cps = [result.get("checkpoint", {})] + result.get("historical_checkpoints", [])
        for cp in all_cps:
            cur.execute(f"INSERT INTO {p}.silver_checkpoints VALUES (?,?,?,?,?,?,?,?,?)",
                        (repo,cp.get("commit_id",commit),cp.get("session_id"),cp.get("prompt"),cp.get("agent_reasoning"),cp.get("checkpoint_summary"),cp.get("author"),cp.get("timestamp"),cp is not all_cps[0]))
            text = " ".join(str(cp.get(k,"")) for k in ("checkpoint_summary","prompt","agent_reasoning"))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",
                        (f"checkpoint:{repo}:{cp.get('commit_id',commit)}",repo,cp.get("commit_id",commit),"checkpoint",None,text,json.dumps(cp,default=str)))
        for t in tests or []:
            cur.execute(f"INSERT INTO {p}.silver_tests VALUES (?,?,?,?,?)",(repo,t["test_id"],t.get("file"),t.get("covers_entity"),t.get("description")))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",
                        (f"test:{repo}:{t['test_id']}",repo,commit,"test",t.get("covers_entity"),json.dumps(t),json.dumps(t,default=str)))
        for changed, item in result["all_affected"].items():
            cur.execute(f"INSERT INTO {p}.gold_change_impact VALUES (?,?,?,?,?,?,?)",
                        (repo,commit,item.get("changed_entity"),changed,item.get("depth",0),item.get("path",""),item.get("source","unknown")))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",
                        (f"impact:{repo}:{commit}:{changed}",repo,commit,"impact",changed,
                         f"Changed entity {item.get('changed_entity')} affects {changed} at depth {item.get('depth',0)}.",json.dumps(item,default=str)))
        cur.execute(f"INSERT INTO {p}.gold_risk_scores VALUES (?,?,?,?,?,?)",
                    (repo,commit,risk["risk_score"],risk["risk_band"],json.dumps(risk["risk_reasons"]),json.dumps(risk["components"])))
        for rec in recommended_tests or []:
            cur.execute(f"INSERT INTO {p}.gold_test_recommendations VALUES (?,?,?,?,?,?)",
                        (repo,commit,rec["test_id"],rec["priority"],rec["relevance_score"],rec["reason"]))
        for m in missed or []:
            cur.execute(f"INSERT INTO {p}.gold_missed_risks VALUES (?,?,?,?,?,?)",
                        (repo,commit,m["entity_id"],m.get("missed_risk_score",0),m["reason"],m.get("supporting_checkpoint_id")))
        cur.execute(f"INSERT INTO {p}.analysis_runs VALUES (?,?,?,?,?,?,?,current_timestamp())",
                    (run_id or f"{repo}:{commit}",repo,commit,risk["risk_score"],risk["risk_band"],llm_engine,"databricks"))
        conn.commit(); cur.close()

    def sql(self, statement: str, params: tuple[Any,...] = ()) -> list[dict[str,Any]]:
        cur=self.connect().cursor(); cur.execute(statement,params)
        cols=[d[0] for d in (cur.description or [])]; rows=cur.fetchall(); cur.close()
        return [dict(zip(cols,row)) for row in rows]

class AISearchStore:
    def __init__(self):
        self.workspace_url=_cfg("DATABRICKS_WORKSPACE_URL")
        self.index_name=_cfg("DATABRICKS_AI_SEARCH_INDEX")
        self.endpoint_name=_cfg("DATABRICKS_AI_SEARCH_ENDPOINT")

    def search(self, query: str, k: int = 8, repo: str | None = None) -> list[dict[str,Any]]:
        if not self.index_name: return []
        from databricks.ai_search.client import AISearchClient
        client=AISearchClient(workspace_url=self.workspace_url) if self.workspace_url else AISearchClient()
        index=client.get_index(index_name=self.index_name, endpoint_name=self.endpoint_name) if self.endpoint_name else client.get_index(index_name=self.index_name)
        kwargs={"query_text":query,"columns":["id","repo","commit_id","doc_type","entity_id","text","metadata_json"],"num_results":k,"query_type":"hybrid"}
        if repo: kwargs["filters"] = f"repo = '{repo.replace(chr(39), chr(39)*2)}'"
        return _parse_result(index.similarity_search(**kwargs))

def _parse_result(result: Any) -> list[dict[str,Any]]:
    if not isinstance(result,dict): return []
    cols=[c.get("name",c) if isinstance(c,dict) else c for c in result.get("manifest",{}).get("columns",[])]
    rows=result.get("result",{}).get("data_array",[])
    # Databricks AI Search returns the requested columns plus score in some API versions;
    # never assume the final requested column is the score.
    out=[]
    for row in rows:
        item=dict(zip(cols,row))
        for key in ("score","_score","similarity"):
            if key in item: break
        else:
            if isinstance(result.get("result",{}).get("row_count"), int) and len(row)>len(cols):
                item["score"]=row[-1]
            else: item["score"]=None
        if item.get("metadata_json"):
            try: item["metadata"]=json.loads(item["metadata_json"])
            except Exception: pass
        out.append(item)
    return out
