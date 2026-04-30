from __future__ import annotations

from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.file_handlers import extract_submission_content


def extractor_agent(state: EvaluationState) -> EvaluationState:
    validation = state["validation_result"]
    state["extracted_content"] = ""
    state["extraction_metadata"] = {}
    if (not validation.get("valid")) and validation.get("type") == "other":
        return state
    if not validation.get("url"):
        return state
    content, metadata = extract_submission_content(
        validation["url"],
        validation["type"],
        state["config"]["app_config"].request_timeout_seconds,
    )
    max_chars = state["config"]["app_config"].max_content_chars
    state["extracted_content"] = content[:max_chars]
    state["extraction_metadata"] = metadata
    return state

