import json
import re
from typing import Any

import httpx
import ollama

from local_rag.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = ollama.Client(host=self.settings.ollama_host)

    def health_check(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.settings.ollama_host}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                names = [m.get("name", "") for m in models]
                return {"ok": True, "models": names}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        stream: bool = False,
    ) -> str:
        response = self._client.chat(
            model=self.settings.ollama_model,
            messages=messages,
            options={"temperature": temperature},
            stream=stream,
        )
        if stream:
            parts: list[str] = []
            for chunk in response:
                parts.append(chunk["message"]["content"])
            return "".join(parts)
        return response["message"]["content"]

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raw = self.chat(messages, temperature=temperature)
        return _parse_json(raw)


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
