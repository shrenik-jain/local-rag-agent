from local_rag.ingestion.pipeline import IngestPipeline


def test_delete_sources(tmp_path):
    doc = tmp_path / "sample.txt"
    doc.write_text("Alpha beta gamma content for retrieval testing.")
    pipeline = IngestPipeline("test-delete")
    pipeline.ingest_paths([doc])
    assert pipeline.store.count() > 0

    result = pipeline.delete_sources(["sample.txt"])
    assert len(result["deleted"]) == 1
    assert result["deleted"][0]["chunks_removed"] > 0
    assert pipeline.store.count() == 0

    missing = pipeline.delete_sources(["sample.txt"])
    assert missing["not_found"] == ["sample.txt"]

    pipeline.store.reset()
    pipeline.graph.reset()
