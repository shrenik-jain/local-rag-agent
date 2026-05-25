from local_rag.config import get_settings
from local_rag.models import RetrievedChunk

REFUSAL_MESSAGE = (
    "I don't have enough relevant information in your uploaded documents to answer "
    "that question confidently. Try rephrasing or adding more source files."
)


def has_sufficient_context(chunks: list[RetrievedChunk]) -> bool:
    """True when graded chunks exist. Rerank scores are cross-encoder logits, not 0-1."""
    return len(chunks) > 0
