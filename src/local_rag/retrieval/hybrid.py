from collections import defaultdict
from typing import Sequence

from rank_bm25 import BM25Okapi

from local_rag.config import get_settings
from local_rag.models import DocumentChunk, RetrievedChunk
from local_rag.retrieval.kg_retriever import KGRetriever
from local_rag.retrieval.reranker import rerank
from local_rag.storage.chroma_store import ChromaStore


class HybridRetriever:
    def __init__(self, collection_name: str = "default") -> None:
        self.collection_name = collection_name
        self.store = ChromaStore(collection_name)
        self.kg = KGRetriever(collection_name)
        self._bm25: BM25Okapi | None = None
        self._bm25_chunks: list[DocumentChunk] = []

    def rebuild_bm25(self) -> None:
        self._bm25_chunks = self.store.get_all_chunks()
        if not self._bm25_chunks:
            self._bm25 = None
            return
        tokenized = [c.text.lower().split() for c in self._bm25_chunks]
        self._bm25 = BM25Okapi(tokenized)

    def _bm25_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if self._bm25 is None or not self._bm25_chunks:
            self.rebuild_bm25()
        if self._bm25 is None:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results: list[RetrievedChunk] = []
        for rank, idx in enumerate(ranked_idx):
            if scores[idx] <= 0:
                continue
            results.append(
                RetrievedChunk(
                    chunk=self._bm25_chunks[idx],
                    score=float(scores[idx]),
                    rank=rank + 1,
                )
            )
        return results

    def retrieve(
        self,
        query: str,
        *,
        source_filter: Sequence[str] | None = None,
        use_kg: bool = True,
    ) -> list[RetrievedChunk]:
        settings = get_settings()
        dense = self.store.dense_search(
            query, top_k=settings.retrieval_top_k, source_filter=source_filter
        )
        sparse = self._bm25_search(query, settings.retrieval_top_k)
        if source_filter:
            names = set(source_filter)
            dense = [r for r in dense if r.chunk.metadata.get("source_name") in names]
            sparse = [r for r in sparse if r.chunk.metadata.get("source_name") in names]

        fused = reciprocal_rank_fusion([dense, sparse], k=60)

        if use_kg and settings.enable_kg:
            kg_chunk_ids = self.kg.get_boost_chunk_ids(query)
            if kg_chunk_ids:
                id_set = set(kg_chunk_ids)
                all_chunks = {c.chunk_id: c for c in self.store.get_all_chunks()}
                for cid in kg_chunk_ids:
                    if cid in all_chunks and cid not in {f.chunk.chunk_id for f in fused}:
                        fused.append(
                            RetrievedChunk(chunk=all_chunks[cid], score=0.5, rank=0)
                        )

        reranked = rerank(query, fused[: settings.retrieval_top_k])
        return reranked


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]],
    k: int = 60,
) -> list[RetrievedChunk]:
    scores: dict[str, float] = defaultdict(float)
    chunks: dict[str, RetrievedChunk] = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            cid = item.chunk.chunk_id
            scores[cid] += 1.0 / (k + rank + 1)
            chunks[cid] = item
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    fused: list[RetrievedChunk] = []
    for i, cid in enumerate(sorted_ids):
        fused.append(
            RetrievedChunk(chunk=chunks[cid].chunk, score=scores[cid], rank=i + 1)
        )
    return fused
