from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"
    embed_fallback: str = "minilm"

    chroma_path: Path = Path("./data/chroma")
    graph_db_path: Path = Path("./data/graph.db")
    data_dir: Path = Path("./data")

    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 20
    rerank_top_k: int = 6
    min_rerank_score: float = -10.0
    max_agent_retries: int = 2
    max_file_size_mb: int = 50
    enable_kg: bool = True

    allowed_extensions: tuple[str, ...] = (
        ".pdf",
        ".csv",
        ".json",
        ".txt",
        ".md",
        ".docx",
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.graph_db_path.parent.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
