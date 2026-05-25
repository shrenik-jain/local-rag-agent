from dataclasses import dataclass, field

from local_rag.models import AgentResponse


@dataclass
class ChatSession:
    collection: str = "default"
    history: list[tuple[str, str]] = field(default_factory=list)
    max_history: int = 10

    def add_turn(self, user: str, assistant: str) -> None:
        self.history.append((user, assistant))
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

    def context_prefix(self) -> str:
        if not self.history:
            return ""
        lines = []
        for u, a in self.history[-3:]:
            lines.append(f"User: {u}\nAssistant: {a[:300]}")
        return "Previous conversation:\n" + "\n".join(lines) + "\n\n"

    def enrich_query(self, query: str) -> str:
        prefix = self.context_prefix()
        if prefix:
            return prefix + f"Current question: {query}"
        return query

    def record_response(self, query: str, response: AgentResponse) -> None:
        self.add_turn(query, response.answer)
