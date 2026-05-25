from typing import Sequence

import ollama
from sentence_transformers import SentenceTransformer

from local_rag.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._ollama = ollama.Client(host=self.settings.ollama_host)
        self._minilm: SentenceTransformer | None = None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return self._embed_ollama(texts)
        except Exception:
            return self._embed_minilm(texts)

    def _embed_ollama(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            resp = self._ollama.embeddings(
                model=self.settings.ollama_embed_model,
                prompt=text,
            )
            vectors.append(resp["embedding"])
        return vectors

    def _embed_minilm(self, texts: Sequence[str]) -> list[list[float]]:
        if self._minilm is None:
            self._minilm = SentenceTransformer("all-MiniLM-L6-v2")
        encoded = self._minilm.encode(list(texts), convert_to_numpy=True)
        return [vec.tolist() for vec in encoded]
