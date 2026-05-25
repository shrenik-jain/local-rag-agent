import json
import sys
from pathlib import Path
from typing import Optional

import typer

from local_rag.agent.graph import run_agent
from local_rag.chat.session import ChatSession
from local_rag.config import get_settings
from local_rag.ingestion.pipeline import IngestPipeline
from local_rag.llm.ollama_client import OllamaClient
from local_rag.storage.chroma_store import ChromaStore
from local_rag.storage.graph_store import GraphStore

app = typer.Typer(
    name="veridian",
    help="Veridian — private document intelligence. Fully offline.",
    no_args_is_help=True,
)


def _emit(data: dict, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(data, indent=2))
    else:
        for k, v in data.items():
            typer.echo(f"{k}: {v}")


@app.command("ingest")
def ingest(
    paths: list[Path] = typer.Argument(..., help="Files or directories to ingest"),
    collection: str = typer.Option("default", "--collection", "-c", help="Collection name"),
    no_kg: bool = typer.Option(False, "--no-kg", help="Skip knowledge graph extraction"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Ingest one or more files into the local vector index."""
    all_files: list[Path] = []
    for p in paths:
        if p.is_dir():
            settings = get_settings()
            for ext in settings.allowed_extensions:
                all_files.extend(p.rglob(f"*{ext}"))
        else:
            all_files.append(p)

    if not all_files:
        typer.echo("No files found to ingest.", err=True)
        raise typer.Exit(code=1)

    pipeline = IngestPipeline(collection, enable_kg=not no_kg)
    result = pipeline.ingest_paths(all_files)
    _emit(result, json_out)
    if result["errors"]:
        raise typer.Exit(code=2)


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Question to ask"),
    collection: str = typer.Option("default", "--collection", "-c"),
    sources: Optional[list[str]] = typer.Option(None, "--sources", "-s", help="Filter by file names"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Ask a single grounded question."""
    response = run_agent(question, collection=collection, source_filter=sources)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "answer": response.answer,
                    "refused": response.refused,
                    "reason": response.reason,
                    "citations": [
                        {
                            "index": c.index,
                            "source": c.source,
                            "quote": c.quote,
                            "page": c.page,
                        }
                        for c in response.citations
                    ],
                },
                indent=2,
            )
        )
    else:
        typer.echo(response.answer)
        if response.citations:
            typer.echo("\nSources:")
            for c in response.citations:
                page = f" p.{c.page}" if c.page else ""
                typer.echo(f"  [{c.index}] {c.source}{page}: {c.quote[:120]}...")
    if response.refused:
        raise typer.Exit(code=3)


@app.command("chat")
def chat(
    collection: str = typer.Option("default", "--collection", "-c"),
    sources: Optional[list[str]] = typer.Option(None, "--sources", "-s"),
) -> None:
    """Interactive chat REPL with grounded answers."""
    session = ChatSession(collection=collection)
    typer.echo("Veridian — type 'exit' or Ctrl+C to quit")
    while True:
        try:
            query = typer.prompt("You")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nBye.")
            break
        if query.strip().lower() in {"exit", "quit"}:
            break
        response = run_agent(
            query,
            collection=collection,
            source_filter=sources,
            chat_history=session.history,
        )
        typer.echo(f"\nAssistant: {response.answer}\n")
        if response.citations:
            typer.echo("Sources:")
            for c in response.citations:
                typer.echo(f"  [{c.index}] {c.source}")
        session.record_response(query, response)


@app.command("status")
def status(
    collection: str = typer.Option("default", "--collection", "-c"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show Ollama health and index status."""
    settings = get_settings()
    health = OllamaClient().health_check()
    store = ChromaStore(collection)
    graph = GraphStore(collection)
    data = {
        "ollama": health,
        "collection": collection,
        "chunks": store.count(),
        "sources": store.get_indexed_sources(),
        "graph": graph.stats(),
        "models": {
            "llm": settings.ollama_model,
            "embed": settings.ollama_embed_model,
        },
    }
    _emit(data, json_out)


@app.command("delete")
def delete(
    sources: list[str] = typer.Argument(..., help="Source file names to remove from the index"),
    collection: str = typer.Option("default", "--collection", "-c"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Remove one or more indexed files from the vector store and knowledge graph."""
    pipeline = IngestPipeline(collection)
    result = pipeline.delete_sources(sources)
    _emit(result, json_out)
    if not result["deleted"] and result["not_found"]:
        raise typer.Exit(code=1)


@app.command("reset")
def reset(
    collection: str = typer.Option("default", "--collection", "-c"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Delete all indexed data for a collection."""
    store = ChromaStore(collection)
    graph = GraphStore(collection)
    store.reset()
    graph.reset()
    _emit({"collection": collection, "status": "reset"}, json_out)


if __name__ == "__main__":
    app()
