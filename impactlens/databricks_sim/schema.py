"""
Table DDL for the local SQLite stand-in for Databricks Delta Lake.

Table names mirror the doc's proposed Unity Catalog layout:
  bronze.*  -> raw ingested payloads (graph NDJSON, git diffs, checkpoints)
  silver.*  -> normalized entities/relationships/changes/checkpoints
  gold.*    -> decision-ready: change_impact, risk_scores, test_recommendations

Point this module at a real Databricks SQL warehouse by swapping the
sqlite3 connection in pipeline.py for `databricks-sql-connector` and
running the same DDL (Delta syntax is a near-superset of this SQLite DDL).
"""

DDL = """
CREATE TABLE IF NOT EXISTS bronze_raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,          -- 'graph' | 'checkpoint' | 'git'
    repo TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver_code_entities (
    entity_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    kind TEXT,
    file TEXT,
    line INTEGER,
    module TEXT,
    signature TEXT,
    PRIMARY KEY (entity_id, repo, commit_id)
);

CREATE TABLE IF NOT EXISTS silver_code_relationships (
    repo TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    source_entity TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    relationship TEXT DEFAULT 'calls',
    confidence REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS silver_code_changes (
    repo TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    file TEXT NOT NULL,
    entity_id TEXT,
    change_type TEXT,
    author TEXT,
    timestamp TEXT,
    subject TEXT
);

CREATE TABLE IF NOT EXISTS silver_checkpoints (
    repo TEXT,
    commit_id TEXT NOT NULL,
    session_id TEXT,
    prompt TEXT,
    agent_reasoning TEXT,
    checkpoint_summary TEXT,
    author TEXT,
    timestamp TEXT,
    is_historical INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS silver_tests (
    repo TEXT,
    test_id TEXT,
    file TEXT,
    covers_entity TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS gold_change_impact (
    repo TEXT,
    commit_id TEXT,
    changed_entity TEXT,
    affected_entity TEXT,
    depth INTEGER,
    relationship_path TEXT
);

CREATE TABLE IF NOT EXISTS gold_risk_scores (
    repo TEXT,
    commit_id TEXT,
    risk_score REAL,
    risk_band TEXT,
    risk_reasons_json TEXT,
    PRIMARY KEY (repo, commit_id)
);

CREATE TABLE IF NOT EXISTS gold_test_recommendations (
    repo TEXT,
    commit_id TEXT,
    test_id TEXT,
    priority TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS gold_missed_risks (
    repo TEXT,
    commit_id TEXT,
    affected_entity TEXT,
    reason TEXT,
    supporting_checkpoint_id TEXT
);
"""
