from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source_path: str
    file_type: str
    page: int | None = None
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float
    rank: int = 0


@dataclass
class Citation:
    index: int
    source: str
    chunk_id: str
    quote: str
    page: int | None = None


@dataclass
class AgentResponse:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    reason: str = ""
    sources_used: list[str] = field(default_factory=list)
