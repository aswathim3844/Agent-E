from __future__ import annotations

from difflib import SequenceMatcher

def normalize_content(content: str) -> str:
    # Intentionally keep comments and markdown so stylistic artifacts are part of similarity checks.
    text = (content or "").lower()
    return " ".join(text.split())


def similarity_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()

