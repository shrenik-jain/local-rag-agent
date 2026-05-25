from typing import Sequence, TypedDict

from langgraph.graph import END, StateGraph

from local_rag.agent.prompts import (
    GENERATION_USER,
    GROUNDED_SYSTEM,
    REFUSAL_TEMPLATE,
    ROUTER_SYSTEM,
)
from local_rag.agent.tools import AgentTools
from local_rag.config import get_settings
from local_rag.guardrails.faithfulness import verify_answer
from local_rag.guardrails.injection import sanitize_query
from local_rag.guardrails.relevance import grade_chunks, is_broad_document_query
from local_rag.guardrails.thresholds import REFUSAL_MESSAGE, has_sufficient_context
from local_rag.llm.ollama_client import OllamaClient
from local_rag.models import AgentResponse, Citation, RetrievedChunk


class AgentState(TypedDict):
    query: str
    search_query: str
    collection: str
    source_filter: list[str] | None
    chat_history: list[tuple[str, str]] | None
    intent: str
    chunks: list[RetrievedChunk]
    answer: str
    citations: list[Citation]
    refused: bool
    reason: str
    retries: int
    use_kg: bool


def build_agent(collection_name: str = "default"):
    tools = AgentTools(collection_name)
    llm = OllamaClient()
    settings = get_settings()

    def route_query(state: AgentState) -> AgentState:
        search_query = state["search_query"]
        query, safe = sanitize_query(search_query)
        if not safe:
            return {
                **state,
                "query": query,
                "search_query": query,
                "refused": True,
                "reason": "Query blocked by safety guardrails.",
                "answer": "I cannot process that request.",
            }
        intent = "factual_qa"
        if is_broad_document_query(query):
            intent = "summary"
        else:
            try:
                result = llm.chat_json(
                    [
                        {"role": "system", "content": ROUTER_SYSTEM},
                        {"role": "user", "content": query},
                    ]
                )
                intent = result.get("intent", "factual_qa")
            except Exception:
                intent = "factual_qa"
        return {**state, "query": query, "search_query": query, "intent": intent, "refused": False}

    def retrieve(state: AgentState) -> AgentState:
        if state.get("refused"):
            return state
        intent = state.get("intent", "factual_qa")
        search_query = state["search_query"]
        if intent == "summary" and state.get("source_filter"):
            answer = tools.summarize_source(state["source_filter"][0])
            return {**state, "answer": answer, "chunks": [], "citations": []}
        if intent == "compare" and state.get("source_filter") and len(state["source_filter"]) >= 2:
            answer = tools.compare_sources(
                state["source_filter"][0],
                state["source_filter"][1],
                search_query,
            )
            return {**state, "answer": answer, "chunks": [], "citations": []}

        chunks = tools.search_documents(
            search_query,
            source_filter=state.get("source_filter"),
        )
        tools.retriever.rebuild_bm25()
        return {**state, "chunks": chunks}

    def grade_documents(state: AgentState) -> AgentState:
        if state.get("refused") or state.get("answer"):
            return state
        lenient = is_broad_document_query(state["search_query"])
        graded = grade_chunks(
            state["search_query"],
            state.get("chunks", []),
            llm,
            lenient=lenient,
        )
        return {**state, "chunks": graded}

    def generate(state: AgentState) -> AgentState:
        if state.get("refused"):
            return state
        if state.get("answer"):
            return state
        chunks = state.get("chunks", [])
        if not has_sufficient_context(chunks):
            return {
                **state,
                "refused": True,
                "reason": "Insufficient retrieval confidence",
                "answer": REFUSAL_MESSAGE,
            }
        context_blocks = []
        for i, c in enumerate(chunks):
            name = c.chunk.metadata.get("source_name", c.chunk.source_path)
            context_blocks.append(f"[{i+1}] ({name})\n{c.chunk.text}")
        context = "\n\n".join(context_blocks)
        history = state.get("chat_history") or []
        history_note = ""
        if history:
            lines = [f"User: {u}\nAssistant: {a[:200]}" for u, a in history[-2:]]
            history_note = "Recent conversation:\n" + "\n".join(lines) + "\n\n"
        messages = [
            {"role": "system", "content": GROUNDED_SYSTEM},
            {
                "role": "user",
                "content": history_note
                + GENERATION_USER.format(context=context, question=state["query"]),
            },
        ]
        answer = llm.chat(messages, temperature=0.1)
        citations = [
            Citation(
                index=i + 1,
                source=c.chunk.metadata.get("source_name", ""),
                chunk_id=c.chunk.chunk_id,
                quote=c.chunk.text[:200],
                page=c.chunk.page,
            )
            for i, c in enumerate(chunks)
        ]
        return {**state, "answer": answer, "citations": citations}

    def verify(state: AgentState) -> AgentState:
        if state.get("refused") or not state.get("chunks"):
            return state
        faithful, revised = verify_answer(
            state["query"], state["answer"], state["chunks"], llm
        )
        if faithful:
            return {**state, "answer": revised}
        retries = state.get("retries", 0) + 1
        if retries >= settings.max_agent_retries:
            return {
                **state,
                "refused": True,
                "reason": "Failed faithfulness verification",
                "answer": REFUSAL_TEMPLATE,
                "retries": retries,
            }
        return {**state, "answer": "", "retries": retries}

    def should_retry(state: AgentState) -> str:
        if state.get("refused"):
            return "end"
        if state.get("answer") and state.get("chunks") and state.get("retries", 0) > 0:
            if not state["answer"]:
                return "generate"
        if (
            not state.get("refused")
            and state.get("chunks")
            and not state.get("answer")
            and state.get("retries", 0) > 0
        ):
            return "generate"
        if (
            not state.get("refused")
            and state.get("chunks")
            and state.get("answer")
            and state.get("retries", 0) > 0
            and state["answer"] == REFUSAL_TEMPLATE
        ):
            return "end"
        retries = state.get("retries", 0)
        if not state.get("refused") and state.get("chunks") and retries > 0 and not state.get("answer"):
            return "generate"
        # Check faithfulness retry path
        if (
            not state.get("refused")
            and state.get("chunks")
            and state.get("retries", 0) > 0
            and state.get("answer") == ""
        ):
            return "generate"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("route", route_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade", grade_documents)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)

    graph.set_entry_point("route")
    graph.add_edge("route", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_edge("grade", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges(
        "verify",
        lambda s: "generate" if (not s.get("refused") and not s.get("answer") and s.get("retries", 0) > 0) else "end",
        {"generate": "generate", "end": END},
    )

    return graph.compile()


def run_agent(
    query: str,
    *,
    collection: str = "default",
    source_filter: Sequence[str] | None = None,
    chat_history: Sequence[tuple[str, str]] | None = None,
) -> AgentResponse:
    agent = build_agent(collection)
    result = agent.invoke(
        {
            "query": query,
            "search_query": query,
            "collection": collection,
            "source_filter": list(source_filter) if source_filter else None,
            "chat_history": list(chat_history) if chat_history else None,
            "intent": "factual_qa",
            "chunks": [],
            "answer": "",
            "citations": [],
            "refused": False,
            "reason": "",
            "retries": 0,
            "use_kg": get_settings().enable_kg,
        }
    )
    sources = list({c.source for c in result.get("citations", []) if c.source})
    return AgentResponse(
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        refused=result.get("refused", False),
        reason=result.get("reason", ""),
        sources_used=sources,
    )
