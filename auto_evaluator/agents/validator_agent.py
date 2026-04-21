from __future__ import annotations

from pathlib import Path

import requests

from auto_evaluator.state import EvaluationState
from auto_evaluator.utils.file_handlers import (
    build_colab_download_url,
    build_drive_download_url,
    build_raw_github_url,
    detect_submission_type,
)


def validator_agent(state: EvaluationState) -> EvaluationState:
    student = state["current_student"]
    url = str(student.get("submission_link", "")).strip()
    timeout_seconds = state["config"]["app_config"].request_timeout_seconds
    submission_type = detect_submission_type(url)
    resolved_url = url
    if submission_type == "colab":
        resolved_url = build_colab_download_url(url)
    elif submission_type == "drive":
        resolved_url = build_drive_download_url(url)
    elif submission_type == "github" and "/blob/" in url:
        resolved_url = build_raw_github_url(url)

    result = {"valid": False, "type": submission_type, "url": resolved_url, "remark": ""}
    if submission_type in {"local_text", "local_dir", "zip"} and not resolved_url.lower().startswith(("http://", "https://")):
        path = Path(resolved_url)
        if path.exists():
            result["valid"] = True
            result["remark"] = "Local submission path is reachable"
        else:
            result["remark"] = "Local submission path does not exist"
        state["validation_result"] = result
        return state
    try:
        response = requests.get(
            resolved_url,
            timeout=timeout_seconds,
            allow_redirects=True,
            headers={"User-Agent": "auto-evaluator/1.0"},
        )
        if response.status_code >= 400:
            result["remark"] = f"Submission link returned HTTP {response.status_code}"
        elif submission_type == "other":
            result["remark"] = "Unsupported submission type"
        else:
            result["valid"] = True
            result["remark"] = "Link is reachable"
    except Exception as exc:
        result["remark"] = f"Invalid or unreachable link: {exc}"
    state["validation_result"] = result
    return state
