import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from local_rag.config import get_settings
from local_rag.models import DocumentChunk


def chunk_segments(
    segments: list[tuple[str, dict]],
    *,
    source_path: Path,
    file_type: str,
    content_hash: str,
) -> list[DocumentChunk]:
    settings = get_settings()
    chunks: list[DocumentChunk] = []
    for text, meta in segments:
        if not text.strip():
            continue
        parts = _split_text(text, settings.chunk_size, settings.chunk_overlap)
        for part in parts:
            chunk_id = str(uuid.uuid4())
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=part,
                    source_path=str(source_path.resolve()),
                    file_type=file_type,
                    page=meta.get("page"),
                    content_hash=content_hash,
                    metadata={
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "source_name": source_path.name,
                    },
                )
            )
    return chunks


def file_content_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
