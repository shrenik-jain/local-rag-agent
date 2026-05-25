#!/usr/bin/env python3
"""Smoke test — requires Ollama running with models pulled."""

import sys
import tempfile
from pathlib import Path

from local_rag.agent.graph import run_agent
from local_rag.ingestion.pipeline import IngestPipeline
from local_rag.llm.ollama_client import OllamaClient


def main() -> int:
    health = OllamaClient().health_check()
    if not health.get("ok"):
        print(f"SKIP: Ollama not available — {health.get('error')}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / "facts.txt"
        doc.write_text(
            "Company Policy: Refunds are available within 30 days of purchase. "
            "Contact support@example.com for help."
        )
        pipeline = IngestPipeline("smoke", enable_kg=False)
        result = pipeline.ingest_paths([doc])
        assert result["ingested"], result

        response = run_agent(
            "What is the refund window?",
            collection="smoke",
        )
        print("Answer:", response.answer)
        print("Refused:", response.refused)
        if response.refused or "30" not in response.answer:
            print("FAIL: expected grounded answer mentioning 30 days")
            return 1

        oob = run_agent("What is the capital of France?", collection="smoke")
        print("OOB refused:", oob.refused)
        print("Smoke test passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
