from __future__ import annotations

import re
from typing import Any


def _safe_snippet(text: str, limit: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned[:limit]


def generate_rubric_from_text(assignment_name: str, pdf_text: str) -> dict[str, Any]:
    text = f"{assignment_name}\n{pdf_text}".lower()
    data_prep_signals = [
        "missing value",
        "imputation",
        "outlier",
        "iqr",
        "scaling",
        "standardscaler",
        "minmax",
        "one-hot",
        "encoding",
        "train test split",
        "sale price",
        "data cleaning",
    ]
    if any(signal in text for signal in data_prep_signals):
        return {
            "max_score": 15,
            "criteria": [
                {
                    "name": "Dataset understanding and profiling",
                    "weight": 2,
                    "description": "Reviews structure, data types, and summary statistics before transformations.",
                },
                {
                    "name": "Data quality checks",
                    "weight": 2,
                    "description": "Checks duplicate records/features and documents cleanup decisions.",
                },
                {
                    "name": "Missing value treatment",
                    "weight": 3,
                    "description": "Applies suitable imputation strategy for numeric and categorical features.",
                },
                {
                    "name": "Feature preparation",
                    "weight": 3,
                    "description": "Uses appropriate scaling/encoding methods while preserving target semantics.",
                },
                {
                    "name": "Outlier handling",
                    "weight": 2,
                    "description": "Identifies and handles extreme/unrealistic values with a defensible method.",
                },
                {
                    "name": "Train-test setup",
                    "weight": 3,
                    "description": "Performs correct target selection and reproducible train/test split.",
                },
            ],
        }
    criteria = []

    if any(keyword in text for keyword in ["correct", "output", "result", "accuracy"]):
        criteria.append(
            {
                "name": "Correctness of output",
                "weight": 7,
                "description": "Expected functionality and correctness against assignment requirements.",
            }
        )
    if any(keyword in text for keyword in ["quality", "structure", "modular", "clean code"]):
        criteria.append(
            {
                "name": "Code quality and structure",
                "weight": 4,
                "description": "Readable, modular, and well-organized implementation.",
            }
        )
    if any(keyword in text for keyword in ["naming", "variable", "function name"]):
        criteria.append(
            {
                "name": "Naming conventions",
                "weight": 2,
                "description": "Clear and consistent naming for files, variables, and functions.",
            }
        )
    if any(keyword in text for keyword in ["documentation", "comment", "readme", "explain"]):
        criteria.append(
            {
                "name": "Documentation and comments",
                "weight": 2,
                "description": "Helpful comments and documentation for understanding usage and logic.",
            }
        )

    if not criteria:
        criteria = [
            {"name": "Correctness of output", "weight": 7, "description": f"Core correctness for {assignment_name}."},
            {"name": "Code quality and structure", "weight": 4, "description": "Readable, modular, and maintainable code."},
            {"name": "Naming conventions", "weight": 2, "description": "Meaningful names used throughout the submission."},
            {"name": "Documentation and comments", "weight": 2, "description": "Comments or usage notes improve clarity."},
        ]

    return {"max_score": 15, "criteria": criteria}


def _count_lines(content: str) -> int:
    return len([line for line in content.splitlines() if line.strip()])


def _comment_ratio(content: str) -> float:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return 0.0
    comment_lines = [line for line in lines if line.startswith("#") or line.startswith("//")]
    return len(comment_lines) / len(lines)


def _function_names(content: str) -> list[str]:
    return re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", content)


def _snake_case_ratio(names: list[str]) -> float:
    if not names:
        return 0.0
    good = [name for name in names if re.fullmatch(r"[a-z]+(?:_[a-z0-9]+)*", name)]
    return len(good) / len(names)


def heuristic_evaluate_submission(rubric: dict[str, Any], extracted_content: str) -> dict[str, Any]:
    content = extracted_content or ""
    lines = _count_lines(content)
    has_imports = bool(re.search(r"^\s*(import|from)\s+", content, re.MULTILINE))
    has_functions = bool(re.search(r"^\s*def\s+", content, re.MULTILINE))
    has_classes = bool(re.search(r"^\s*class\s+", content, re.MULTILINE))
    has_readme_text = "# file:" in content.lower() or bool(re.search(r"readme", content, re.IGNORECASE))
    comment_ratio = _comment_ratio(content)
    names = _function_names(content)
    snake_ratio = _snake_case_ratio(names)

    scores = []
    total = 0.0

    for criterion in rubric.get("criteria", []):
        name = str(criterion.get("name", "")).lower()
        weight = float(criterion.get("weight", 0) or 0)
        awarded = 0.0
        justification = "Minimal evidence found."

        if "correctness" in name or "output" in name:
            coverage = 0.0
            if lines >= 8:
                coverage += 0.35
            if has_imports:
                coverage += 0.2
            if has_functions or has_classes:
                coverage += 0.25
            if re.search(r"(print|return|write|save)", content):
                coverage += 0.2
            awarded = round(min(weight, weight * coverage), 2)
            justification = "Heuristic score based on presence of executable logic and output-related code."
        elif "quality" in name or "structure" in name:
            structure = 0.0
            if lines >= 10:
                structure += 0.3
            if has_functions:
                structure += 0.4
            if has_classes:
                structure += 0.1
            if "# file:" in content.lower():
                structure += 0.2
            awarded = round(min(weight, weight * structure), 2)
            justification = "Heuristic score based on code organization, modularity signals, and file structure."
        elif "naming" in name:
            naming = snake_ratio if names else (0.5 if has_functions else 0.2)
            awarded = round(min(weight, weight * naming), 2)
            justification = "Heuristic score based on detected function naming patterns."
        elif "documentation" in name or "comment" in name:
            docs = 0.0
            if comment_ratio >= 0.15:
                docs = 1.0
            elif comment_ratio >= 0.05:
                docs = 0.6
            elif has_readme_text:
                docs = 0.5
            awarded = round(min(weight, weight * docs), 2)
            justification = "Heuristic score based on comments and documentation-like content."

        total += awarded
        scores.append(
            {
                "name": criterion.get("name", ""),
                "awarded": awarded,
                "weight": weight,
                "justification": justification,
            }
        )

    confidence = 0.55 if content.strip() else 0.0
    remarks = "Heuristic fallback evaluation used."
    if content.strip():
        remarks += f" Submission contains about {lines} non-empty lines. Preview: {_safe_snippet(content)}"

    return {
        "scores_per_criterion": scores,
        "total_score": round(min(15.0, total), 2),
        "remarks": remarks,
        "confidence": confidence,
    }
