from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class AppConfig:
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"
    llm_force_fallback: bool = False
    default_deadline: str = ""
    late_penalty_2_3_days: int = 1
    late_penalty_4_7_days: int = 3
    late_penalty_8_14_days: int = 5
    plagiarism_threshold: float = 0.95
    pass_mark: float = 10.0
    request_timeout_seconds: int = 30
    max_content_chars: int = 50000


def load_config() -> AppConfig:
    load_dotenv()
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        google_model=os.getenv("GOOGLE_MODEL", "gemini-1.5-flash"),
        llm_force_fallback=os.getenv("LLM_FORCE_FALLBACK", "false").lower() == "true",
        default_deadline=os.getenv("DEFAULT_DEADLINE", ""),
        late_penalty_2_3_days=int(os.getenv("LATE_PENALTY_2_3_DAYS", "1")),
        late_penalty_4_7_days=int(os.getenv("LATE_PENALTY_4_7_DAYS", "3")),
        late_penalty_8_14_days=int(os.getenv("LATE_PENALTY_8_14_DAYS", "5")),
        plagiarism_threshold=float(os.getenv("PLAGIARISM_THRESHOLD", "0.95")),
        pass_mark=float(os.getenv("PASS_MARK", "10")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        max_content_chars=int(os.getenv("MAX_CONTENT_CHARS", "50000")),
    )
