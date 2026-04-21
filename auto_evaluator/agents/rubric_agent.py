from __future__ import annotations

from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.file_handlers import extract_pdf_text
from auto_evaluator.utils.heuristics import generate_rubric_from_text
from auto_evaluator.utils.llm_client import LLMClient, build_rubric_prompt


DEFAULT_RUBRIC = {
    "max_score": 15,
    "criteria": [
        {"name": "Correctness of output", "weight": 7, "description": "Expected functionality and correctness."},
        {"name": "Code quality and structure", "weight": 4, "description": "Readable, modular, well-structured code."},
        {"name": "Naming conventions", "weight": 2, "description": "Clear names for files, variables, and functions."},
        {"name": "Documentation and comments", "weight": 2, "description": "Helpful comments and usage instructions."},
    ],
}


def rubric_agent(state: EvaluationState) -> EvaluationState:
    config = state["config"]["app_config"]
    pdf_text = extract_pdf_text(state["pdf_link"], config.request_timeout_seconds)
    llm = LLMClient(config)
    heuristic_rubric = generate_rubric_from_text(state["assignment_name"], pdf_text)
    rubric = llm.call_json(
        build_rubric_prompt(state["assignment_name"], pdf_text),
        fallback=heuristic_rubric or DEFAULT_RUBRIC,
    )
    state["rubric"] = rubric if rubric.get("criteria") else heuristic_rubric or DEFAULT_RUBRIC
    return state
