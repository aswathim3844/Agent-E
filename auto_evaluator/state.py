from __future__ import annotations

from typing import Any, TypedDict


class EvaluationState(TypedDict, total=False):
    assignment_name: str
    pdf_link: str
    deadline: str
    rubric: dict[str, Any]
    students: list[dict[str, Any]]
    current_student_index: int
    current_student: dict[str, Any]
    validation_result: dict[str, Any]
    extracted_content: str
    extraction_metadata: dict[str, Any]
    evaluation_result: dict[str, Any]
    final_results: list[dict[str, Any]]
    all_extracted_contents: list[dict[str, Any]]
    config: dict[str, Any]

