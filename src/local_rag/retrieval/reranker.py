from local_rag.config import get_settings
from local_rag.models import RetrievedChunk

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def rerank(query: str, chunks: list[RetrievedChunk], top_k: int | None = None) -> list[RetrievedChunk]:
    if not chunks:
        return []
    settings = get_settings()
    k = top_k or settings.rerank_top_k
    model = _get_reranker()
    pairs = [(query, c.chunk.text) for c in chunks]
    scores = model.predict(pairs)
    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )
    result: list[RetrievedChunk] = []
    for i, (chunk, score) in enumerate(ranked[:k]):
        result.append(
            RetrievedChunk(chunk=chunk.chunk, score=float(score), rank=i + 1)
        )
    return result
