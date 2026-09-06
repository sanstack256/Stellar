"""
databricks_sim.ai_search
--------------------------
Stand-in for Databricks AI Search's Delta-synced vector index. We use a
local TF-IDF + cosine similarity index over `silver_checkpoints` so the
whole demo runs offline with no embedding API key required.

Swap `CheckpointIndex` for a real `databricks-vectorsearch` client backed
by a Delta-synced index on `silver_checkpoints` — the query interface
(`search(query, k)`) is designed to match.
"""

from __future__ import annotations
import sqlite3
from integrations.databricks import enabled as db_enabled, AISearchStore
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class CheckpointIndex:
    def __init__(self, conn: sqlite3.Connection, repo: str):
        self.conn = conn
        self.repo = repo
        self.real = AISearchStore() if db_enabled() else None
        self._rows = []
        self._vectorizer = None
        self._matrix = None
        self._build()

    def _build(self):
        cur = self.conn.execute(
            "SELECT commit_id, session_id, prompt, agent_reasoning, checkpoint_summary, author, timestamp, is_historical "
            "FROM silver_checkpoints WHERE repo=?",
            (self.repo,),
        )
        self._rows = [
            {
                "commit_id": r[0], "session_id": r[1], "prompt": r[2] or "",
                "agent_reasoning": r[3] or "", "checkpoint_summary": r[4] or "",
                "author": r[5], "timestamp": r[6], "is_historical": bool(r[7]),
            }
            for r in cur.fetchall()
        ]
        if not self._rows:
            return
        corpus = [
            f"{r['checkpoint_summary']} {r['prompt']} {r['agent_reasoning']}"
            for r in self._rows
        ]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, k: int = 5, historical_only: bool = False) -> list[dict]:
        if self.real and getattr(self.real, "index_name", None):
            try:
                real_results = self.real.search(query, k)
                if historical_only:
                    real_results = [r for r in real_results if r.get("is_historical", True)]
                if real_results:
                    return real_results
                # Real index configured but returned nothing (e.g. empty/unsynced
                # index) -- fall through to the local index rather than silently
                # dropping historical-match evidence.
            except Exception:
                pass
        if not self._rows or self._vectorizer is None:
            return []
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(zip(self._rows, sims), key=lambda x: -x[1])
        results = []
        for row, score in ranked:
            if historical_only and not row["is_historical"]:
                continue
            if score <= 0:
                continue
            results.append({**row, "score": round(float(score), 4)})
            if len(results) >= k:
                break
        return results
