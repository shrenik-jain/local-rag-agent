import json
import sqlite3
from pathlib import Path

import networkx as nx

from local_rag.config import get_settings
from local_rag.llm.ollama_client import OllamaClient


class GraphStore:
    def __init__(self, collection_name: str = "default") -> None:
        self.settings = get_settings()
        self.collection_name = collection_name
        self.db_path = self.settings.graph_db_path
        self._graph = nx.DiGraph()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS triples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    source_name TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_triples_collection ON triples(collection)"
            )

    def extract_and_store(
        self,
        chunk_id: str,
        text: str,
        source_name: str,
        *,
        llm: OllamaClient | None = None,
    ) -> int:
        if not self.settings.enable_kg:
            return 0
        client = llm or OllamaClient()
        prompt = [
            {
                "role": "system",
                "content": (
                    "Extract entity-relation triples from the text. "
                    'Return JSON: {"triples": [{"subject": "...", "relation": "...", "object": "..."}]} '
                    "Max 5 triples. Only facts explicitly in the text."
                ),
            },
            {"role": "user", "content": text[:2000]},
        ]
        try:
            data = client.chat_json(prompt)
            triples = data.get("triples", [])
        except Exception:
            return 0

        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for t in triples:
                subj = str(t.get("subject", "")).strip()
                rel = str(t.get("relation", "")).strip()
                obj = str(t.get("object", "")).strip()
                if not subj or not rel or not obj:
                    continue
                conn.execute(
                    "INSERT INTO triples (collection, subject, relation, object, chunk_id, source_name) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (self.collection_name, subj, rel, obj, chunk_id, source_name),
                )
                self._graph.add_edge(subj, obj, relation=rel, chunk_id=chunk_id)
                count += 1
        return count

    def search_by_entities(self, entities: list[str], hops: int = 2) -> list[str]:
        chunk_ids: set[str] = set()
        with sqlite3.connect(self.db_path) as conn:
            for entity in entities:
                rows = conn.execute(
                    "SELECT chunk_id, subject, object FROM triples "
                    "WHERE collection = ? AND (LOWER(subject) LIKE ? OR LOWER(object) LIKE ?)",
                    (self.collection_name, f"%{entity.lower()}%", f"%{entity.lower()}%"),
                ).fetchall()
                for chunk_id, subj, obj in rows:
                    chunk_ids.add(chunk_id)
                    if hops >= 2:
                        for _, _, data in self._graph.out_edges(subj, data=True):
                            if data.get("chunk_id"):
                                chunk_ids.add(data["chunk_id"])
                        for _, _, data in self._graph.out_edges(obj, data=True):
                            if data.get("chunk_id"):
                                chunk_ids.add(data["chunk_id"])
        return list(chunk_ids)

    def delete_by_source_name(self, source_name: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM triples WHERE collection = ? AND source_name = ?",
                (self.collection_name, source_name),
            )
            return cur.rowcount

    def reset(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM triples WHERE collection = ?", (self.collection_name,))
        self._graph.clear()

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM triples WHERE collection = ?",
                (self.collection_name,),
            ).fetchone()
        return {"triples": row[0] if row else 0}
