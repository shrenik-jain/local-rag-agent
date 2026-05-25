from pathlib import Path
from typing import Sequence

import chromadb
from chromadb.config import Settings as ChromaSettings

from local_rag.config import get_settings
from local_rag.embeddings.ollama_embed import EmbeddingService
from local_rag.models import DocumentChunk, RetrievedChunk


class ChromaStore:
    def __init__(self, collection_name: str = "default") -> None:
        self.settings = get_settings()
        self.collection_name = collection_name
        self.embedder = EmbeddingService()
        self._client = chromadb.PersistentClient(
            path=str(self.settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "source_path": c.source_path,
                "source_name": c.metadata.get("source_name", Path(c.source_path).name),
                "file_type": c.file_type,
                "page": c.page if c.page is not None else -1,
                "content_hash": c.content_hash,
            }
            for c in chunks
        ]
        embeddings = self.embedder.embed(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(chunks)

    def delete_by_source(self, source_path: str) -> None:
        existing = self._collection.get(where={"source_path": source_path})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def delete_by_source_name(self, source_name: str) -> int:
        existing = self._collection.get(where={"source_name": source_name})
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def get_indexed_sources(self) -> list[dict]:
        data = self._collection.get(include=["metadatas"])
        seen: dict[str, dict] = {}
        for meta in data.get("metadatas") or []:
            if not meta:
                continue
            sp = meta.get("source_path", "")
            if sp not in seen:
                seen[sp] = {
                    "source_path": sp,
                    "source_name": meta.get("source_name", Path(sp).name),
                    "file_type": meta.get("file_type", ""),
                }
        return list(seen.values())

    def dense_search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        source_filter: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k or self.settings.retrieval_top_k
        query_emb = self.embedder.embed([query])[0]
        where = None
        if source_filter:
            names = list(source_filter)
            if len(names) == 1:
                where = {"source_name": names[0]}
        results = self._collection.query(
            query_embeddings=[query_emb],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        retrieved: list[RetrievedChunk] = []
        ids = results["ids"][0] if results["ids"] else []
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        dists = results["distances"][0] if results["distances"] else []
        for i, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            chunk = DocumentChunk(
                chunk_id=cid,
                text=doc or "",
                source_path=meta.get("source_path", ""),
                file_type=meta.get("file_type", ""),
                page=meta.get("page") if meta.get("page", -1) >= 0 else None,
                content_hash=meta.get("content_hash", ""),
                metadata={"source_name": meta.get("source_name", "")},
            )
            score = 1.0 - float(dist) if dist is not None else 0.0
            retrieved.append(RetrievedChunk(chunk=chunk, score=score, rank=i + 1))
        return retrieved

    def get_all_chunks(self) -> list[DocumentChunk]:
        data = self._collection.get(include=["documents", "metadatas"])
        chunks: list[DocumentChunk] = []
        for cid, doc, meta in zip(
            data.get("ids") or [],
            data.get("documents") or [],
            data.get("metadatas") or [],
        ):
            if not meta:
                continue
            chunks.append(
                DocumentChunk(
                    chunk_id=cid,
                    text=doc or "",
                    source_path=meta.get("source_path", ""),
                    file_type=meta.get("file_type", ""),
                    page=meta.get("page") if meta.get("page", -1) >= 0 else None,
                    content_hash=meta.get("content_hash", ""),
                    metadata={"source_name": meta.get("source_name", "")},
                )
            )
        return chunks

    def get_source_content_hash(self, source_path: str) -> str | None:
        data = self._collection.get(where={"source_path": source_path})
        metas = data.get("metadatas") or []
        if metas:
            return metas[0].get("content_hash")
        return None

    def reset(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self._collection.count()
