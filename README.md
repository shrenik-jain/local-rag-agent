# VaultMind

**Private Document Intelligence** — ingest your files and receive grounded, citation-backed answers. Fully offline.

VaultMind combines hybrid retrieval, reranking, and faithfulness guardrails so responses stay tied to your source material. No cloud APIs required after initial model download.

---

## Features

- **Multi-format ingestion** — PDF, CSV, JSON, TXT, MD, DOCX
- **Hybrid retrieval** — vector search + BM25 + cross-encoder reranking
- **Knowledge graph boost** — lightweight entity linking for multi-hop questions
- **Grounded answers** — citations, relevance grading, and faithfulness checks
- **Fully local** — LLM, embeddings, vector store, and graph storage on your machine
- **CLI + web UI** — scriptable commands and a Gradio interface

---

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download)
- [Python `venv`](https://docs.python.org/3/library/venv.html) (recommended)
- 16 GB RAM (recommended)

---

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

For development (tests):

```bash
pip install -e ".[dev]"
```

### 3. Pull Ollama models

Download models once while you have network access. These are the defaults:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

**Alternative models** (more capable, higher RAM use):

```bash
ollama pull mistral:7b-instruct-q4_K_M
```

If you change models, update your `.env` file (see below).

### 4. Configure environment (optional)

Copy the example environment file and edit as needed:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Chat / reasoning model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `ENABLE_KG` | `true` | Enable knowledge graph extraction on ingest |

### 5. Verify installation

```bash
local-rag status
pytest tests/
```

Optional end-to-end check (requires Ollama running):

```bash
python scripts/smoke_test.py
```

---

## Usage

### Web Interface (VaultMind UI)

```bash
local-rag-web
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

1. Upload documents in the **Document library** panel
2. Click **Index documents**
3. Ask questions in the **Assistant** chat
4. Use **Limit search to** (under Query settings) to scope queries to specific files
5. Use **Remove selected** to delete files from the index

### CLI

```bash
# Index files or directories
local-rag ingest ./docs --collection mydocs

# Single question
local-rag ask "What is the refund policy?" --collection mydocs

# Interactive chat
local-rag chat --collection mydocs

# Check system and index status
local-rag status --json

# Remove specific files from the index
local-rag delete "report.pdf" --collection mydocs

# Wipe an entire collection
local-rag reset --collection mydocs
```

Filter answers to specific files:

```bash
local-rag ask "Summarize the policy" --collection mydocs --sources policy.pdf
```

Skip knowledge graph extraction during ingest (faster, vector-only):

```bash
local-rag ingest ./docs --no-kg
```

---

## Architecture

```
Documents → loaders → chunking → embeddings → ChromaDB
                               ↘ entity extraction → SQLite + NetworkX

Question → hybrid retrieval (dense + BM25 + KG) → rerank → grade → generate → verify → answer
```

| Layer | Technology |
|-------|------------|
| LLM | [Ollama](https://ollama.com) |
| Embeddings | Ollama `nomic-embed-text` (fallback: MiniLM) |
| Vector store | ChromaDB (local persistence) |
| Sparse search | BM25 |
| Reranker | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) |
| Knowledge graph | SQLite + NetworkX |
| Agent orchestration | LangGraph |
| Web UI | Gradio |
| CLI | Typer |

---

## Offline operation

After Ollama models are pulled, VaultMind runs without internet access. All inference, embedding, indexing, and storage happen on your device. Data is written to the local `./data/` directory.

---

## Project structure

```
local-rag-agent/
├── app/                  # Gradio web UI (VaultMind)
├── cli/                  # Typer CLI entry point
├── src/local_rag/        # Core library (ingestion, retrieval, agent, guardrails)
├── tests/                # Unit tests
├── scripts/              # Smoke test script
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Troubleshooting

| Issue | Suggestion |
|-------|------------|
| `Ollama not reachable` | Start Ollama: `ollama serve` |
| Refusal despite indexed docs | Rephrase the question; try unchecking **Limit search to**; restart the web UI after code updates |
| Slow first ingest | Normal — embeddings and optional KG extraction run locally |
| Out of memory | Use `llama3.2:3b` instead of a 7B+ model; ingest fewer files at once |

---

## Contributing

Contributions are welcome. To propose a change:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-change`)
3. Make your changes and add tests where appropriate
4. Run `pytest tests/` and ensure they pass
5. Open a pull request with a clear description of the change

Please keep pull requests focused and include steps to verify the behavior.

---

## Questions & Support

If you run into issues or have questions:

- Open a [GitHub issue](https://github.com/shrenikjain9/local-rag-agent/issues)
- Reach out to the maintainer: [Shrenik Jain](https://shrenik-jain.github.io/contact.html)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.
