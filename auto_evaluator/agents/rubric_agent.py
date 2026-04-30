from __future__ import annotations

from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.file_handlers import extract_pdf_text
from auto_evaluator.utils.heuristics import generate_rubric_from_text
from auto_evaluator.utils.llm_client import LLMClient, build_rubric_prompt


DEFAULT_RUBRIC = {
    "max_score": 15,
    "criteria": [
        {
            "name": "Dataset understanding and profiling",
            "weight": 2,
            "description": "Reviews schema, data types, and summary statistics before transformation.",
        },
        {
            "name": "Data quality checks",
            "weight": 2,
            "description": "Checks duplicates and records cleanup decisions clearly.",
        },
        {
            "name": "Missing value treatment",
            "weight": 3,
            "description": "Uses appropriate imputation strategy for numeric and categorical data.",
        },
        {
            "name": "Feature preparation",
            "weight": 3,
            "description": "Applies scaling/encoding correctly without distorting target semantics.",
        },
        {
            "name": "Outlier handling",
            "weight": 2,
            "description": "Identifies and treats unrealistic/extreme values with a robust method.",
        },
        {
            "name": "Train-test setup",
            "weight": 3,
            "description": "Builds correct target split and reproducible train/test partition.",
        },
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
