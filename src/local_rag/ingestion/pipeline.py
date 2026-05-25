from pathlib import Path

from local_rag.guardrails.injection import sanitize_document_text
from local_rag.ingestion.chunking import chunk_segments, file_content_hash
from local_rag.ingestion.loaders import LoaderError, load_document
from local_rag.llm.ollama_client import OllamaClient
from local_rag.retrieval.hybrid import HybridRetriever
from local_rag.storage.chroma_store import ChromaStore
from local_rag.storage.graph_store import GraphStore


class IngestPipeline:
    def __init__(self, collection_name: str = "default", *, enable_kg: bool | None = None) -> None:
        self.collection_name = collection_name
        self.store = ChromaStore(collection_name)
        self.graph = GraphStore(collection_name)
        self.retriever = HybridRetriever(collection_name)
        self._enable_kg = enable_kg
        self._llm = OllamaClient()

    def ingest_paths(self, paths: list[Path], *, skip_unchanged: bool = True) -> dict:
        results = {"ingested": [], "skipped": [], "errors": []}
        for path in paths:
            path = path.resolve()
            if not path.exists():
                results["errors"].append({"path": str(path), "error": "Not found"})
                continue
            try:
                info = self.ingest_file(path, skip_unchanged=skip_unchanged)
                if info.get("skipped"):
                    results["skipped"].append(info)
                else:
                    results["ingested"].append(info)
            except (LoaderError, Exception) as exc:
                results["errors"].append({"path": str(path), "error": str(exc)})
        self.retriever.rebuild_bm25()
        return results

    def ingest_file(self, path: Path, *, skip_unchanged: bool = True) -> dict:
        content_hash = file_content_hash(path)
        source_path = str(path.resolve())

        existing = self.store.get_indexed_sources()
        for src in existing:
            if src["source_path"] == source_path:
                stored_hash = self.store.get_source_content_hash(source_path)
                if stored_hash == content_hash and skip_unchanged:
                    return {
                        "source": path.name,
                        "skipped": True,
                        "reason": "unchanged",
                        "chunks": 0,
                    }
                self.store.delete_by_source(source_path)

        segments = load_document(path)
        all_chunks = []
        for text, meta in segments:
            text = sanitize_document_text(text)
            chunks = chunk_segments(
                [(text, meta)],
                source_path=path,
                file_type=path.suffix.lower(),
                content_hash=content_hash,
            )
            all_chunks.extend(chunks)

        count = self.store.upsert_chunks(all_chunks)

        kg_count = 0
        if self._enable_kg is not False:
            for chunk in all_chunks[:20]:
                kg_count += self.graph.extract_and_store(
                    chunk.chunk_id,
                    chunk.text,
                    chunk.metadata.get("source_name", path.name),
                    llm=self._llm,
                )

        return {
            "source": path.name,
            "skipped": False,
            "chunks": count,
            "triples": kg_count,
        }

    def delete_sources(self, source_names: list[str]) -> dict:
        deleted: list[dict] = []
        not_found: list[str] = []
        indexed = {s["source_name"] for s in self.store.get_indexed_sources()}

        for name in source_names:
            if name not in indexed:
                not_found.append(name)
                continue
            chunks_removed = self.store.delete_by_source_name(name)
            triples_removed = self.graph.delete_by_source_name(name)
            deleted.append(
                {
                    "source": name,
                    "chunks_removed": chunks_removed,
                    "triples_removed": triples_removed,
                }
            )

        if deleted:
            self.retriever.rebuild_bm25()
        return {"deleted": deleted, "not_found": not_found}
