import re

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(the\s+)?system\s+prompt",
    r"you\s+are\s+now\s+(a\s+)?(?:DAN|jailbreak)",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"override\s+safety",
]


def sanitize_query(query: str) -> tuple[str, bool]:
    """Return (sanitized_query, is_safe)."""
    text = query.strip()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return text, False
    return text, True


def sanitize_document_text(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in _INJECTION_PATTERNS):
            cleaned.append("[redacted instruction-like line]")
        else:
            cleaned.append(line)
    return "\n".join(cleaned)
