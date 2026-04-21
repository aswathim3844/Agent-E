from __future__ import annotations

import argparse
import logging
from typing import Any

from auto_evaluator.agents.evaluator_agent import evaluator_agent
from auto_evaluator.agents.extractor_agent import extractor_agent
from auto_evaluator.agents.validator_agent import validator_agent
from auto_evaluator.orchestration.graph import build_report_graph, build_rubric_graph
from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.config import load_config
from auto_evaluator.utils.file_handlers import read_input_excel
from auto_evaluator.utils.plagiarism import normalize_content


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def prepare_state(input_path: str, output_path: str) -> EvaluationState:
    config = load_config()
    assignment, students = read_input_excel(input_path)
    deadline = assignment.get("deadline") or config.default_deadline or ""
    pdf_link = str(assignment.get("pdf_link", "")).strip()
    if not pdf_link:
        raise ValueError("The assignment sheet must include a non-empty pdf_link.")
    return EvaluationState(
        assignment_name=str(assignment.get("assignment_name", "Assignment")),
        pdf_link=pdf_link,
        deadline=str(deadline),
        students=students,
        current_student_index=0,
        final_results=[],
        all_extracted_contents=[],
        config={
            "app_config": config,
            "input_path": input_path,
            "output_path": output_path,
        },
    )


def process_students(state: EvaluationState) -> EvaluationState:
    extracted_cache: list[dict[str, Any]] = []

    for student in state["students"]:
        state["current_student"] = student
        state = validator_agent(state)
        state = extractor_agent(state)
        extracted_cache.append(
            {
                "student_name": student.get("student_name", ""),
                "normalized_content": normalize_content(state.get("extracted_content", "")),
            }
        )
        student["_cached_validation_result"] = dict(state["validation_result"])
        student["_cached_extracted_content"] = state.get("extracted_content", "")
        student["_cached_extraction_metadata"] = dict(state.get("extraction_metadata", {}))

    state["all_extracted_contents"] = extracted_cache

    final_results = []
    for student in state["students"]:
        state["current_student"] = student
        state["validation_result"] = student["_cached_validation_result"]
        state["extracted_content"] = student["_cached_extracted_content"]
        state["extraction_metadata"] = student["_cached_extraction_metadata"]
        state = evaluator_agent(state)
        result = {
            "student_name": student.get("student_name", ""),
            "submission_link": student.get("submission_link", ""),
            **state["evaluation_result"],
        }
        final_results.append(result)

    state["final_results"] = final_results
    return state


def run(input_path: str, output_path: str) -> EvaluationState:
    state = prepare_state(input_path, output_path)
    state = build_rubric_graph().invoke(state)
    state = process_students(state)
    state = build_report_graph().invoke(state)
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate student assignment submissions from Excel.")
    parser.add_argument("--input", default="samples/input.xlsx", help="Path to input Excel file")
    parser.add_argument("--output", default="samples/output.xlsx", help="Path to output Excel file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.input, args.output)
