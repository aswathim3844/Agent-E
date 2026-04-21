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

    for result in state.get("final_results", []):
        summary_rows.append(
            {
                "Student Name": result["student_name"],
                "Submission Link": result["submission_link"],
                "Total Marks (out of 20)": result["final_total"],
                "Evaluation Score (out of 15)": result["quality_score"],
                "Plagiarism Flag": "Yes" if result["plagiarized"] else "No",
                "Matched With": result["matched_with"] or "",
                "Days Late": result["days_late"],
                "Late Penalty (marks deducted from 5)": result["late_penalty_marks"],
                "Needs Review": "Yes" if result["needs_manual_review"] else "No",
                "Review Reason": result["review_reason"],
                "Remarks": result["remarks"],
                "Status": "Pass" if result["final_total"] >= pass_mark else "Fail",
            }
        )
        for criterion in result.get("scores_per_criterion", []):
            detail_rows.append(
                {
                    "Student Name": result["student_name"],
                    "Criterion": criterion.get("name", ""),
                    "Awarded": criterion.get("awarded", 0),
                    "Weight": criterion.get("weight", 0),
                    "Justification": criterion.get("justification", ""),
                }
            )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="summary")
        pd.DataFrame(detail_rows).to_excel(writer, index=False, sheet_name="detailed_breakdown")
    return state

