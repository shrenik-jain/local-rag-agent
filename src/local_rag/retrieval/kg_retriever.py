import re

from local_rag.llm.ollama_client import OllamaClient
from local_rag.storage.graph_store import GraphStore


class KGRetriever:
    def __init__(self, collection_name: str = "default") -> None:
        self.graph = GraphStore(collection_name)

    def get_boost_chunk_ids(self, query: str) -> list[str]:
        entities = _extract_entities(query)
        if not entities:
            return []
        return self.graph.search_by_entities(entities)


def _extract_entities(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query)
    stop = {"what", "when", "where", "which", "who", "how", "the", "and", "for", "from", "about"}
    return [w for w in words if w.lower() not in stop][:8]
