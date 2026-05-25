import re

from local_rag.llm.ollama_client import OllamaClient
from local_rag.models import RetrievedChunk

_BROAD_DOC_PATTERNS = [
    r"what is (this|the) document about",
    r"summarize (this|the) document",
    r"give me an overview",
    r"what does (this|the) document (cover|contain|discuss)",
]


def is_broad_document_query(query: str) -> bool:
    q = query.strip().lower()
    return any(re.search(p, q) for p in _BROAD_DOC_PATTERNS)


def grade_chunks(
    query: str,
    chunks: list[RetrievedChunk],
    llm: OllamaClient | None = None,
    *,
    lenient: bool = False,
) -> list[RetrievedChunk]:
    if not chunks:
        return []
    if lenient:
        return chunks[:6]
    client = llm or OllamaClient()
    relevant: list[RetrievedChunk] = []
    for chunk in chunks:
        prompt = [
            {
                "role": "system",
                "content": (
                    'Grade if the document chunk is relevant to the question. '
                    'Reply JSON only: {"relevant": true} or {"relevant": false}'
                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nChunk:\n{chunk.chunk.text[:1500]}",
            },
        ]
        try:
            result = client.chat_json(prompt)
            if result.get("relevant"):
                relevant.append(chunk)
        except Exception:
            relevant.append(chunk)
    # If grader is overly strict, keep top chunks rather than refusing everything.
    if not relevant and chunks:
        return chunks[:3]
    return relevant
