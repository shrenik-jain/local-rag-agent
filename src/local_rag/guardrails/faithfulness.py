from local_rag.llm.ollama_client import OllamaClient
from local_rag.models import RetrievedChunk


def verify_answer(
    query: str,
    answer: str,
    chunks: list[RetrievedChunk],
    llm: OllamaClient | None = None,
) -> tuple[bool, str]:
    if not chunks:
        return False, answer
    client = llm or OllamaClient()
    context = "\n\n---\n\n".join(
        f"[{i+1}] {c.chunk.text[:800]}" for i, c in enumerate(chunks)
    )
    prompt = [
        {
            "role": "system",
            "content": (
                "Check if the answer is fully supported by the context. "
                'Return JSON: {"faithful": true/false, "revised_answer": "..."} '
                "If not faithful, revise to only include supported claims or empty string."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {query}\n\nContext:\n{context}\n\nAnswer:\n{answer}",
        },
    ]
    try:
        result = client.chat_json(prompt)
        faithful = bool(result.get("faithful", False))
        revised = str(result.get("revised_answer", answer)).strip()
        return faithful, revised or answer
    except Exception:
        return True, answer
