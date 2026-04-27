from __future__ import annotations

from typing import Any

from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.heuristics import heuristic_evaluate_submission
from auto_evaluator.utils.late_penalty import (
    apply_excessive_late_reduction,
    calculate_days_late,
    calculate_late_penalty,
)
from auto_evaluator.utils.llm_client import LLMClient, build_evaluation_prompt
from auto_evaluator.utils.plagiarism import normalize_content, similarity_score


def _fallback_evaluation(rubric: dict[str, Any], remark: str) -> dict[str, Any]:
    return {
        "scores_per_criterion": [
            {"name": item["name"], "awarded": 0, "weight": item["weight"], "justification": remark}
            for item in rubric.get("criteria", [])
        ],
        "total_score": 0,
        "remarks": remark,
        "confidence": 0.0,
    }


def evaluator_agent(state: EvaluationState) -> EvaluationState:
    config = state["config"]["app_config"]
    student = state["current_student"]
    validation = state["validation_result"]
    extracted_content = state.get("extracted_content", "")
    rubric = state["rubric"]
    remarks: list[str] = []

    if not validation.get("valid"):
        evaluation = _fallback_evaluation(rubric, validation.get("remark", "Invalid submission"))
    elif not extracted_content.strip():
        evaluation = _fallback_evaluation(rubric, "No extractable content")
        remarks.append(state.get("extraction_metadata", {}).get("error", ""))
    else:
        llm = LLMClient(config)
        evaluation = llm.call_json(
            build_evaluation_prompt(rubric, extracted_content),
            fallback=heuristic_evaluate_submission(rubric, extracted_content),
        )

    normalized_current = normalize_content(extracted_content)
    plagiarized = False
    matched_with = None
    plagiarism_score = 0.0
    for item in state.get("all_extracted_contents", []):
        if item["student_name"] == student.get("student_name"):
            continue
        other_normalized = item.get("normalized_content", "")
        score = similarity_score(normalized_current, other_normalized)
        if score >= config.plagiarism_threshold:
            plagiarized = True
            matched_with = item["student_name"]
            plagiarism_score = score
            remarks.append(f"Possible exact-copy plagiarism detected with {matched_with} ({score:.2f}).")
            break

    days_late = calculate_days_late(student.get("submission_timestamp"), state["deadline"])
    late_penalty, capped = calculate_late_penalty(days_late, config)

    quality_score = float(evaluation.get("total_score", 0) or 0)
    quality_score = max(0.0, min(15.0, quality_score))

    if plagiarized:
        final_total = 0.0
    else:
        available_penalty_pool = 5 - min(5, late_penalty)
        raw_total = quality_score + available_penalty_pool
        final_total = min(10.0, raw_total) if capped else min(20.0, raw_total)
        final_total = apply_excessive_late_reduction(final_total, days_late)

    confidence = float(evaluation.get("confidence", 0) or 0)
    needs_manual_review = (
        confidence < 0.7
        or not validation.get("valid")
        or not extracted_content.strip()
        or bool(state.get("extraction_metadata", {}).get("error"))
    )
    if needs_manual_review and confidence < 0.7:
        remarks.append("Low-confidence LLM evaluation. Recommended for manual verification.")

    if evaluation.get("remarks"):
        remarks.append(str(evaluation["remarks"]))
    if validation.get("remark"):
        remarks.append(str(validation["remark"]))
    if state.get("extraction_metadata", {}).get("error"):
        remarks.append(str(state["extraction_metadata"]["error"]))

    state["evaluation_result"] = {
        "quality_score": round(quality_score, 2),
        "scores_per_criterion": evaluation.get("scores_per_criterion", []),
        "plagiarized": plagiarized,
        "matched_with": matched_with,
        "plagiarism_score": round(plagiarism_score, 4),
        "days_late": days_late,
        "late_penalty_marks": late_penalty,
        "validation_status": validation.get("validation_status", "invalid"),
        "final_total": round(final_total, 2),
        "needs_manual_review": needs_manual_review,
        "review_reason": "; ".join([item for item in remarks if item])[:2000],
        "remarks": "; ".join([item for item in remarks if item])[:4000],
    }
    return state
