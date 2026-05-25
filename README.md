# Veridian

**Private document intelligence** — ingest your files and receive grounded, citation-backed answers. Fully offline.

Veridian combines hybrid retrieval (dense vectors, BM25, optional knowledge graph), reranking, and faithfulness guardrails so responses stay tied to your source material.

## Requirements

- macOS Apple Silicon (16GB RAM tested profile)
- [Ollama](https://ollama.com) installed and running locally
- Python 3.12 virtualenv at `/Users/shrenikjain9/Documents/virtual_envs/rag`

## Setup

```bash
# Activate the project virtualenv
source /Users/shrenikjain9/Documents/virtual_envs/rag/bin/activate

# From repo root
cd /Users/shrenikjain9/Documents/github/local_rag
pip install -r requirements.txt
pip install -e .

# Pull models (once, while online)
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Optional config
cp .env.example .env
```

## Usage

### CLI

```bash
local-rag ingest ./docs --collection mydocs
local-rag ask "What is the refund policy?" --collection mydocs
local-rag chat --collection mydocs
local-rag status --json
local-rag delete "old-report.pdf" --collection mydocs
local-rag reset --collection mydocs
```

### Web interface

```bash
local-rag-web
# Open http://127.0.0.1:7860
```

Upload documents, index them, scope queries, and converse with the assistant. All processing remains on your device.

## Architecture

- **Embeddings**: Ollama `nomic-embed-text` (fallback: MiniLM)
- **Vector DB**: ChromaDB (`./data/chroma/`)
- **Hybrid retrieval**: dense + BM25 (RRF) + cross-encoder rerank
- **KG**: lightweight triple extraction → SQLite + NetworkX
- **Agent**: LangGraph pipeline (route → retrieve → grade → generate → verify)
- **Guardrails**: injection filter, relevance grading, faithfulness check, refuse on low confidence

## Tests

```bash
pytest tests/
python scripts/smoke_test.py   # requires Ollama
```

## Offline operation

After models are pulled via Ollama, disconnect from the network. All inference, embeddings, and storage remain local.
