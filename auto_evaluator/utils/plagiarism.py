from __future__ import annotations

import re
from difflib import SequenceMatcher


def strip_comments(content: str) -> str:
    without_block_comments = re.sub(r"'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"", "", content)
    without_hash_comments = re.sub(r"#.*", "", without_block_comments)
    without_cpp_comments = re.sub(r"//.*", "", without_hash_comments)
    without_c_blocks = re.sub(r"/\*[\s\S]*?\*/", "", without_cpp_comments)
    return without_c_blocks


def normalize_content(content: str) -> str:
    text = strip_comments(content or "")
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    return text


def similarity_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()

