"""Databricks data plane for ImpactLens.

All workspace-specific identifiers come from environment configuration. The
application writes raw evidence, normalized graph/checkpoint/test data and
decision-ready analysis records to Delta tables, then retrieves the unified
knowledge corpus through Databricks AI Search.
"""
from __future__ import annotations
import json, os, re
from typing import Any


def enabled() -> bool:
    return os.getenv("DATABRICKS_ENABLED", "false").lower() in {"1","true","yes","on"}

def required(name: str) -> str:
    value=os.getenv(name,"").strip()
    if not value: raise RuntimeError(f"{name} is required")
    return value

def ident(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value): raise ValueError(f"Unsafe SQL identifier: {value}")
    return value

class DatabricksStore:
    def __init__(self):
        self.server_hostname=required("DATABRICKS_SERVER_HOSTNAME")
        self.http_path=required("DATABRICKS_HTTP_PATH")
        self.token=required("DATABRICKS_TOKEN")
        self.catalog=ident(required("DATABRICKS_CATALOG"))
        self.schema=ident(required("DATABRICKS_SCHEMA"))
        self._conn=None
    def connect(self):
        if self._conn: return self._conn
        from databricks import sql
        self._conn=sql.connect(server_hostname=self.server_hostname,http_path=self.http_path,access_token=self.token)
        return self._conn
    @property
    def prefix(self): return f"`{self.catalog}`.`{self.schema}`"
    def init(self):
        conn=self.connect(); cur=conn.cursor(); p=self.prefix
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {p}")
        ddl=[
          f"CREATE TABLE IF NOT EXISTS {p}.bronze_raw_events (event_id STRING, source STRING, repo STRING, commit_id STRING, payload_json STRING, ingested_at TIMESTAMP) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.silver_code_entities (entity_id STRING, repo STRING, commit_id STRING, kind STRING, file STRING, line INT, module STRING, signature STRING, raw_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.silver_code_relationships (repo STRING, commit_id STRING, source_entity STRING, target_entity STRING, relationship STRING, depth INT, evidence_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.silver_code_changes (repo STRING, commit_id STRING, file STRING, entity_id STRING, change_type STRING, author STRING, timestamp STRING, subject STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.silver_checkpoints (repo STRING, commit_id STRING, session_id STRING, prompt STRING, agent_reasoning STRING, checkpoint_summary STRING, author STRING, timestamp STRING, is_historical BOOLEAN, raw_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.silver_tests (repo STRING, test_id STRING, file STRING, description STRING, inventory_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.gold_change_impact (repo STRING, commit_id STRING, changed_entity STRING, affected_entity STRING, depth INT, relationship STRING, source STRING, evidence_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.gold_risk_scores (repo STRING, commit_id STRING, risk_score DOUBLE, risk_band STRING, risk_reasons_json STRING, components_json STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.gold_test_recommendations (repo STRING, commit_id STRING, test_id STRING, priority STRING, relevance_score DOUBLE, reason STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.gold_missed_risks (repo STRING, commit_id STRING, affected_entity STRING, missed_risk_score DOUBLE, reason STRING, supporting_checkpoint_id STRING) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.knowledge_documents (id STRING, repo STRING, commit_id STRING, doc_type STRING, entity_id STRING, text STRING, metadata_json STRING, updated_at TIMESTAMP) USING DELTA",
          f"CREATE TABLE IF NOT EXISTS {p}.analysis_runs (run_id STRING, repo STRING, commit_id STRING, risk_score DOUBLE, risk_band STRING, llm_engine STRING, data_plane STRING, created_at TIMESTAMP) USING DELTA",
        ]
        for statement in ddl: cur.execute(statement)
        conn.commit(); cur.close()
    def write(self,result,risk,tests=None,recommended_tests=None,missed=None,run_id=None,llm_engine="unknown"):
        self.init(); cur=self._conn.cursor(); p=self.prefix; repo=result["repo"]; commit=result["commit"]
        for table in ("gold_change_impact","gold_risk_scores","gold_test_recommendations","gold_missed_risks","analysis_runs"):
            cur.execute(f"DELETE FROM {p}.{table} WHERE repo=? AND commit_id=?",(repo,commit))
        cur.execute(f"DELETE FROM {p}.knowledge_documents WHERE repo=? AND commit_id=?",(repo,commit))
        entities=result.get("graph_snapshot",{}).get("rows",[])
        relationships=[]
        for evidence in result.get("graph_evidence",[]):
            for rel_type in ("callers","callees"):
                for item in evidence.get(rel_type,[]):
                    relationships.append({"source":evidence.get("symbol"),"target":item.get("entity_id"),"relationship":rel_type,"depth":item.get("depth",1),"raw":item})
        payloads={"graph":result.get("graph_snapshot",{}),"graph_impact":result.get("graph_evidence",[]),"checkpoint":result.get("checkpoint",{}),"git":{"changed_files":result.get("changed_files",[]),"commit_meta":result.get("commit_meta",{})}}
        for source,payload in payloads.items():
            cur.execute(f"INSERT INTO {p}.bronze_raw_events VALUES (?,?,?,?,?,current_timestamp())",(f"{repo}:{commit}:{source}",source,repo,commit,json.dumps(payload,default=str)))
        for e in entities:
            cur.execute(f"INSERT INTO {p}.silver_code_entities VALUES (?,?,?,?,?,?,?,?,?)",(str(e.get("entity_id")),repo,commit,str(e.get("kind")),e.get("file"),int(e.get("line") or 0),e.get("module"),e.get("signature"),json.dumps(e,default=str)))
        for r in relationships:
            cur.execute(f"INSERT INTO {p}.silver_code_relationships VALUES (?,?,?,?,?,?,?)",(repo,commit,r["source"],r["target"],r["relationship"],int(r["depth"]),json.dumps(r["raw"],default=str)))
        meta=result.get("commit_meta",{})
        for f in result.get("changed_files",[]): cur.execute(f"INSERT INTO {p}.silver_code_changes VALUES (?,?,?,?,?,?,?,?)",(repo,commit,f,None,"changed",meta.get("author"),meta.get("date"),meta.get("subject")))
        cps=[result.get("checkpoint",{})]+result.get("historical_checkpoints",[])
        for i,cp in enumerate(cps):
            cur.execute(f"INSERT INTO {p}.silver_checkpoints VALUES (?,?,?,?,?,?,?,?,?,?)",(repo,cp.get("commit_id",commit),cp.get("session_id"),cp.get("prompt"),cp.get("agent_reasoning"),cp.get("checkpoint_summary"),cp.get("author"),cp.get("timestamp"),i>0,json.dumps(cp,default=str)))
            text=" ".join(str(cp.get(k,"")) for k in ("checkpoint_summary","prompt","agent_reasoning"))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",(f"checkpoint:{repo}:{cp.get('commit_id',commit)}",repo,cp.get("commit_id",commit),"checkpoint",None,text,json.dumps(cp,default=str)))
        for t in tests or []:
            cur.execute(f"INSERT INTO {p}.silver_tests VALUES (?,?,?,?,?)",(repo,t["test_id"],t.get("file"),t.get("description"),json.dumps(t,default=str)))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",(f"test:{repo}:{t['test_id']}",repo,commit,"test",None,t.get("description",t["test_id"]),json.dumps(t,default=str)))
        for eid,item in result.get("all_affected",{}).items():
            cur.execute(f"INSERT INTO {p}.gold_change_impact VALUES (?,?,?,?,?,?,?,?)",(repo,commit,item.get("changed_entity"),eid,item.get("depth",0),item.get("relationship"),item.get("source"),json.dumps(item,default=str)))
            cur.execute(f"INSERT INTO {p}.knowledge_documents VALUES (?,?,?,?,?,?,?,current_timestamp())",(f"impact:{repo}:{commit}:{eid}",repo,commit,"impact",eid,f"Changed entity {item.get('changed_entity')} has a graph relationship to {eid} at depth {item.get('depth',0)}.",json.dumps(item,default=str)))
        cur.execute(f"INSERT INTO {p}.gold_risk_scores VALUES (?,?,?,?,?,?)",(repo,commit,risk["risk_score"],risk["risk_band"],json.dumps(risk["risk_reasons"]),json.dumps(risk["components"])))
        for rec in recommended_tests or []: cur.execute(f"INSERT INTO {p}.gold_test_recommendations VALUES (?,?,?,?,?,?)",(repo,commit,rec["test_id"],rec["priority"],rec["relevance_score"],rec["reason"]))
        for m in missed or []: cur.execute(f"INSERT INTO {p}.gold_missed_risks VALUES (?,?,?,?,?,?)",(repo,commit,m["entity_id"],m.get("missed_risk_score",0),m["reason"],m.get("supporting_checkpoint_id")))
        cur.execute(f"INSERT INTO {p}.analysis_runs VALUES (?,?,?,?,?,?,?,current_timestamp())",(run_id,repo,commit,risk["risk_score"],risk["risk_band"],llm_engine,"databricks"))
        self._conn.commit(); cur.close()
    def sql(self,statement,params=()):
        cur=self.connect().cursor(); cur.execute(statement,params); cols=[d[0] for d in (cur.description or [])]; rows=cur.fetchall(); cur.close(); return [dict(zip(cols,row)) for row in rows]

class AISearchStore:
    def __init__(self):
        self.workspace_url=required("DATABRICKS_WORKSPACE_URL")
        self.index_name=required("DATABRICKS_AI_SEARCH_INDEX")
        self.endpoint_name=os.getenv("DATABRICKS_AI_SEARCH_ENDPOINT","").strip() or None
    def search(self,query,k=8,repo=None):
        from databricks.ai_search.client import AISearchClient
        client=AISearchClient(workspace_url=self.workspace_url)
        index=client.get_index(index_name=self.index_name,endpoint_name=self.endpoint_name) if self.endpoint_name else client.get_index(index_name=self.index_name)
        kwargs={"query_text":query,"columns":["id","repo","commit_id","doc_type","entity_id","text","metadata_json"],"num_results":k,"query_type":"hybrid"}
        if repo: kwargs["filters"]=f"repo = '{repo.replace(chr(39),chr(39)*2)}'"
        return _parse_result(index.similarity_search(**kwargs))

def _parse_result(result):
    if not isinstance(result,dict): return []
    manifest=result.get("manifest",{}).get("columns",[]); cols=[c.get("name",c) if isinstance(c,dict) else c for c in manifest]
    rows=result.get("result",{}).get("data_array",[]); out=[]
    for row in rows:
        item=dict(zip(cols,row))
        if item.get("metadata_json"):
            try:item["metadata"]=json.loads(item["metadata_json"])
            except Exception:pass
        out.append(item)
    return out
