from __future__ import annotations

from pathlib import Path

import pandas as pd

from auto_evaluator.state import EvaluationState


def report_agent(state: EvaluationState) -> EvaluationState:
    output_path = Path(state["config"]["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    detail_rows = []
    pass_mark = state["config"]["app_config"].pass_mark
    check_plagiarism = state.get("config", {}).get("check_plagiarism", True)
    rubric_criteria = [str(item.get("name", "")).strip() for item in (state.get("rubric", {}) or {}).get("criteria", [])]

    for result in state.get("final_results", []):
        passed = result["final_total"] >= pass_mark
        criteria_scores: dict[str, object] = {f"Rubric - {name}": "NA" for name in rubric_criteria if name}
        if passed:
            for criterion in result.get("scores_per_criterion", []) or []:
                criterion_name = str(criterion.get("name", "")).strip()
                if criterion_name:
                    criteria_scores[f"Rubric - {criterion_name}"] = criterion.get("awarded", 0)

        summary_row = {
            "Student Name": result["student_name"],
            "Submission Link": result["submission_link"],
            "Validation Status": result.get("validation_status", "invalid"),
            "Total Marks (out of 20)": result["final_total"],
            "Evaluation Score (out of 15)": result["quality_score"],
            "Days Late": result["days_late"],
            "Late Penalty (marks deducted from 5)": result["late_penalty_marks"],
            "Needs Review": "Yes" if result["needs_manual_review"] else "No",
            "Remarks": "Passed" if passed else result["remarks"],
            "Status": "Pass" if passed else "Fail",
        }
        summary_row.update(criteria_scores)
        if check_plagiarism:
            summary_row["Plagiarism Flag"] = "Yes" if result["plagiarized"] else "No"
            summary_row["Similarity Score"] = result.get("similarity_score", result.get("plagiarism_score", 0.0))
            summary_row["Matched With"] = result["matched_with"] or ""
        summary_rows.append(summary_row)
        criteria = result.get("scores_per_criterion", [])
        for criterion in criteria:
            detail_rows.append(
                {
                    "Student Name": result["student_name"],
                    "Validation Status": result.get("validation_status", "invalid"),
                    "Criterion": criterion.get("name", ""),
                    "Awarded": criterion.get("awarded", 0),
                    "Weight": criterion.get("weight", 0),
                    "Justification": criterion.get("justification", ""),
                    "Remarks": result["remarks"],
                }
            )
        if not criteria:
            # Keep invalid or non-extractable submissions visible in the detailed report too.
            detail_rows.append(
                {
                    "Student Name": result["student_name"],
                    "Validation Status": result.get("validation_status", "invalid"),
                    "Criterion": "",
                    "Awarded": 0,
                    "Weight": 0,
                    "Justification": "",
                    "Remarks": result["remarks"],
                }
            )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="summary")
        pd.DataFrame(detail_rows).to_excel(writer, index=False, sheet_name="detailed_breakdown")
        rubric = state.get("rubric", {}) or {}
        rubric_rows = []
        for item in rubric.get("criteria", []):
            rubric_rows.append(
                {
                    "Criterion": item.get("name", ""),
                    "Weight": item.get("weight", 0),
                    "Description": item.get("description", ""),
                }
            )
        pd.DataFrame(rubric_rows).to_excel(writer, index=False, sheet_name="rubric")
    return state

