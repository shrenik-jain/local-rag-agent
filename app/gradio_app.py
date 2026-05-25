from html import escape
from pathlib import Path

import gradio as gr

from app.branding import (
    CUSTOM_CSS,
    PRODUCT_INTRO,
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
)
from local_rag.agent.graph import run_agent
from local_rag.chat.session import ChatSession
from local_rag.config import get_settings
from local_rag.ingestion.pipeline import IngestPipeline
from local_rag.llm.ollama_client import OllamaClient
from local_rag.storage.chroma_store import ChromaStore

COLLECTION = "default"
_session = ChatSession(collection=COLLECTION)


def _build_theme() -> gr.themes.Base:
    return (
        gr.themes.Base(
            primary_hue=gr.themes.colors.slate,
            secondary_hue=gr.themes.colors.gray,
            neutral_hue=gr.themes.colors.zinc,
        )
        .set(
            body_background_fill="#090a0d",
            body_background_fill_dark="#090a0d",
            block_background_fill="#111318",
            block_background_fill_dark="#111318",
            block_border_color="#252a34",
            block_border_width="1px",
            block_label_text_color="#8b92a0",
            block_title_text_color="#eceef2",
            body_text_color="#eceef2",
            body_text_color_subdued="#8b92a0",
            button_primary_background_fill="#5c7f9e",
            button_primary_background_fill_hover="#6d8fad",
            button_primary_text_color="#ffffff",
            input_background_fill="#171a21",
            input_border_color="#252a34",
        )
    )


def _header_html() -> str:
    return f"""
    <div class="va-shell">
        <div class="va-header">
            <h1 class="va-brand">{PRODUCT_NAME}</h1>
            <p class="va-tagline">{PRODUCT_TAGLINE}</p>
            <p class="va-intro">{PRODUCT_INTRO}</p>
        </div>
    </div>
    """


def _health_html() -> str:
    health = OllamaClient().health_check()
    settings = get_settings()
    if health.get("ok"):
        dot = '<span class="va-status-dot online"></span>'
        status = "Connected"
        llm = settings.ollama_model
        embed = settings.ollama_embed_model
    else:
        dot = '<span class="va-status-dot offline"></span>'
        status = health.get("error", "Unavailable")
        llm = "—"
        embed = "—"
    return f"""
    <div class="va-status-card">
        <p class="va-section-label">System</p>
        <div class="va-status-row"><span>{dot}Runtime</span><span>{status}</span></div>
        <div class="va-status-row"><span>Language model</span><span>{llm}</span></div>
        <div class="va-status-row"><span>Embeddings</span><span>{embed}</span></div>
    </div>
    """


def _sources_dataframe() -> list[list]:
    store = ChromaStore(COLLECTION)
    sources = store.get_indexed_sources()
    chunks = store.get_all_chunks()
    counts: dict[str, int] = {}
    for c in chunks:
        name = c.metadata.get("source_name", Path(c.source_path).name)
        counts[name] = counts.get(name, 0) + 1
    rows = []
    for s in sources:
        name = s.get("source_name", "")
        rows.append([name, s.get("file_type", ""), counts.get(name, 0), "Indexed"])
    return rows


def _source_choices() -> list[str]:
    return [row[0] for row in _sources_dataframe()]


def _refresh_choices() -> tuple[gr.CheckboxGroup, gr.CheckboxGroup]:
    choices = _source_choices()
    return gr.CheckboxGroup(choices=choices), gr.CheckboxGroup(choices=choices)


def delete_files(source_names: list[str]) -> tuple[list[list], str, gr.CheckboxGroup, gr.CheckboxGroup]:
    if not source_names:
        scoped, delete = _refresh_choices()
        return _sources_dataframe(), "Select one or more documents to remove.", delete, scoped
    pipeline = IngestPipeline(COLLECTION)
    result = pipeline.delete_sources(source_names)
    parts = []
    for item in result["deleted"]:
        parts.append(f"Removed {item['source']} ({item['chunks_removed']} segments)")
    for name in result["not_found"]:
        parts.append(f"Not found: {name}")
    scoped, delete = _refresh_choices()
    return _sources_dataframe(), "\n".join(parts) or "Complete.", delete, scoped


def ingest_files(files, progress=gr.Progress()) -> tuple[list[list], str, gr.CheckboxGroup, gr.CheckboxGroup]:
    scoped, delete = _refresh_choices()
    if not files:
        return _sources_dataframe(), "No files selected.", scoped, delete
    pipeline = IngestPipeline(COLLECTION)
    paths = [Path(f) for f in files]
    progress(0.2, desc="Processing documents")
    result = pipeline.ingest_paths(paths, skip_unchanged=True)
    progress(1.0, desc="Complete")
    msg_parts = []
    for item in result["ingested"]:
        msg_parts.append(f"Indexed {item['source']} — {item['chunks']} segments")
    for item in result["skipped"]:
        msg_parts.append(f"Unchanged: {item['source']}")
    for err in result["errors"]:
        msg_parts.append(f"Error ({err['path']}): {err['error']}")
    scoped, delete = _refresh_choices()
    return _sources_dataframe(), "\n".join(msg_parts) or "Complete.", scoped, delete


def _compact_excerpt(text: str, limit: int = 130) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    trimmed = collapsed[:limit].rsplit(" ", 1)[0]
    return trimmed + "…"


def _format_citations(response) -> str:
    refused_class = " va-answer-refused" if response.refused else ""
    if not response.citations:
        return f'<div class="va-answer{refused_class}">{response.answer}</div>'

    seen: set[tuple[str, int | None, str]] = set()
    cards: list[str] = []
    for c in response.citations:
        excerpt = _compact_excerpt(c.quote)
        key = (c.source, c.page, excerpt)
        if key in seen:
            continue
        seen.add(key)

        page_html = (
            f'<span class="va-cite-page">p. {c.page}</span>' if c.page else ""
        )
        cards.append(
            f'<div class="va-cite-item">'
            f'<div class="va-cite-meta">'
            f'<span class="va-cite-num">{c.index}</span>'
            f'<span class="va-cite-file">{escape(c.source)}</span>'
            f"{page_html}"
            f"</div>"
            f'<p class="va-cite-excerpt">{escape(excerpt)}</p>'
            f"</div>"
        )

    if not cards:
        refused_class = " va-answer-refused" if response.refused else ""
        return f'<div class="va-answer{refused_class}">{response.answer}</div>'

    cites_block = (
        '<div class="va-cites">'
        '<p class="va-cites-label">Sources</p>'
        + "".join(cards)
        + "</div>"
    )
    refused_class = " va-answer-refused" if response.refused else ""
    answer_block = f'<div class="va-answer{refused_class}">{response.answer}</div>'
    return f"{answer_block}\n\n{cites_block}"


def chat_fn(message, history, scoped_files, enable_kg):
    settings = get_settings()
    settings.enable_kg = enable_kg
    source_filter = scoped_files if scoped_files else None
    response = run_agent(
        message,
        collection=COLLECTION,
        source_filter=source_filter,
        chat_history=_session.history,
    )
    _session.record_response(message, response)
    full_answer = _format_citations(response)
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": full_answer})
    return history, ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title=f"{PRODUCT_NAME} — {PRODUCT_TAGLINE}") as demo:
        gr.HTML(_header_html())

        with gr.Row(equal_height=False):
            with gr.Column(scale=4, min_width=340):
                gr.HTML(_health_html())

                gr.Markdown('<p class="va-panel-title">Document library</p>')

                with gr.Group():
                    files = gr.File(
                        label="Upload",
                        file_count="multiple",
                        file_types=[".pdf", ".csv", ".json", ".txt", ".md", ".docx"],
                    )
                    with gr.Row():
                        ingest_btn = gr.Button("Index documents", variant="primary", scale=1)
                        delete_btn = gr.Button("Remove selected", variant="secondary", scale=1)

                ingest_status = gr.Textbox(
                    label="Activity",
                    lines=2,
                    interactive=False,
                    placeholder="Index status will appear here.",
                )

                docs_table = gr.Dataframe(
                    headers=["Document", "Format", "Segments", "Status"],
                    label="Indexed corpus",
                    value=_sources_dataframe(),
                    interactive=False,
                )

                delete_select = gr.CheckboxGroup(
                    label="Select to remove",
                    choices=_source_choices(),
                )

                with gr.Accordion("Query settings", open=False):
                    scoped = gr.CheckboxGroup(
                        label="Limit search to",
                        choices=_source_choices(),
                    )
                    enable_kg = gr.Checkbox(
                        label="Knowledge graph enrichment",
                        value=True,
                    )

            with gr.Column(scale=6, min_width=480, elem_classes=["va-chat-column"]):
                gr.Markdown('<p class="va-panel-title">Assistant</p>')
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=540,
                    show_label=False,
                    layout="bubble",
                    placeholder="Your conversation will appear here.",
                    sanitize_html=False,
                    render_markdown=True,
                    group_consecutive_messages=True,
                )
                with gr.Row(elem_classes=["va-composer-row"]):
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="What does the documentation say about…",
                        show_label=False,
                        scale=8,
                        lines=1,
                        max_lines=4,
                        elem_classes=["va-composer-input"],
                    )
                    send = gr.Button("Send", variant="primary", scale=1, min_width=96)

        ingest_btn.click(
            ingest_files,
            inputs=[files],
            outputs=[docs_table, ingest_status, scoped, delete_select],
        )
        delete_btn.click(
            delete_files,
            inputs=[delete_select],
            outputs=[docs_table, ingest_status, delete_select, scoped],
        )
        send.click(
            chat_fn,
            inputs=[msg, chatbot, scoped, enable_kg],
            outputs=[chatbot, msg],
        )
        msg.submit(
            chat_fn,
            inputs=[msg, chatbot, scoped, enable_kg],
            outputs=[chatbot, msg],
        )

    return demo


def main() -> None:
    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        theme=_build_theme(),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
