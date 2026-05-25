from typing import Sequence

from local_rag.llm.ollama_client import OllamaClient
from local_rag.models import RetrievedChunk
from local_rag.retrieval.hybrid import HybridRetriever
from local_rag.storage.chroma_store import ChromaStore
from local_rag.storage.graph_store import GraphStore


class AgentTools:
    def __init__(self, collection_name: str = "default") -> None:
        self.collection_name = collection_name
        self.retriever = HybridRetriever(collection_name)
        self.store = ChromaStore(collection_name)
        self.graph = GraphStore(collection_name)
        self.llm = OllamaClient()

    def search_documents(
        self,
        query: str,
        *,
        source_filter: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        return self.retriever.retrieve(query, source_filter=source_filter)

    def search_knowledge_graph(self, query: str) -> list[str]:
        from local_rag.retrieval.kg_retriever import _extract_entities

        entities = _extract_entities(query)
        return self.graph.search_by_entities(entities)

    def list_indexed_sources(self) -> list[dict]:
        return self.store.get_indexed_sources()

    def summarize_source(self, source_name: str) -> str:
        chunks = [
            c
            for c in self.store.get_all_chunks()
            if c.metadata.get("source_name") == source_name
        ]
        if not chunks:
            return f"No document found: {source_name}"
        text = "\n\n".join(c.text[:500] for c in chunks[:10])
        messages = [
            {"role": "system", "content": "Summarize the document excerpts concisely."},
            {"role": "user", "content": text},
        ]
        return self.llm.chat(messages, temperature=0.2)

    def compare_sources(self, source_a: str, source_b: str, query: str) -> str:
        chunks_a = self.search_documents(query, source_filter=[source_a])
        chunks_b = self.search_documents(query, source_filter=[source_b])
        ctx_a = "\n".join(c.chunk.text[:400] for c in chunks_a[:3])
        ctx_b = "\n".join(c.chunk.text[:400] for c in chunks_b[:3])
        messages = [
            {
                "role": "system",
                "content": "Compare the two document excerpts based only on the text provided.",
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nDocument A ({source_a}):\n{ctx_a}\n\nDocument B ({source_b}):\n{ctx_b}",
            },
        ]
        return self.llm.chat(messages, temperature=0.2)
