import json
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader

from local_rag.config import get_settings


class LoaderError(Exception):
    pass


def load_document(path: Path) -> list[tuple[str, dict]]:
    """Return list of (text, metadata) segments from a file."""
    settings = get_settings()
    suffix = path.suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise LoaderError(f"Unsupported file type: {suffix}")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if path.stat().st_size > max_bytes:
        raise LoaderError(f"File too large (max {settings.max_file_size_mb}MB): {path.name}")

    loaders = {
        ".pdf": _load_pdf,
        ".csv": _load_csv,
        ".json": _load_json,
        ".txt": _load_text,
        ".md": _load_text,
        ".docx": _load_docx,
    }
    loader = loaders.get(suffix)
    if loader is None:
        raise LoaderError(f"No loader for {suffix}")
    return loader(path)


def _load_pdf(path: Path) -> list[tuple[str, dict]]:
    reader = PdfReader(str(path))
    segments: list[tuple[str, dict]] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append((text, {"page": i + 1}))
    if not segments:
        segments.append(("", {"page": 1}))
    return segments


def _load_csv(path: Path) -> list[tuple[str, dict]]:
    df = pd.read_csv(path)
    text = df.to_csv(index=False)
    return [(text, {"page": None})]


def _load_json(path: Path) -> list[tuple[str, dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, indent=2)
    return [(text, {"page": None})]


def _load_text(path: Path) -> list[tuple[str, dict]]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return [(text, {"page": None})]


def _load_docx(path: Path) -> list[tuple[str, dict]]:
    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    return [(text or "", {"page": None})]
