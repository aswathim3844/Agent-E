from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

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

    result = {
        "valid": False,
        "validation_status": "warning_invalid",
        "type": submission_type,
        "url": resolved_url,
        "remark": "unsupported_link_type",
    }
    if submission_type in {"local_text", "local_dir", "zip"} and not resolved_url.lower().startswith(("http://", "https://")):
        path = Path(resolved_url)
        if path.exists():
            result["valid"] = True
            result["validation_status"] = "valid"
            result["remark"] = "valid_local_path"
        else:
            result["remark"] = "invalid_local_path"
        state["validation_result"] = result
        return state
    if submission_type == "other":
        state["validation_result"] = result
        return state
    parsed = urlparse(resolved_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        result["remark"] = "unsupported_link_type"
        state["validation_result"] = result
        return state
    try:
        response = requests.get(
            resolved_url,
            timeout=timeout_seconds,
            allow_redirects=True,
            headers={"User-Agent": "auto-evaluator/1.0"},
        )
        content_type = (response.headers.get("Content-Type") or "").lower()
        content_len = len(response.content or b"")
        if response.status_code in {401, 403}:
            result["remark"] = "private_or_auth_required"
        elif response.status_code >= 400:
            result["remark"] = "network_error"
        elif content_len == 0:
            result["remark"] = "empty_content"
        elif submission_type == "zip" and "zip" not in content_type and not resolved_url.lower().endswith(".zip"):
            result["remark"] = "not_downloadable"
        elif submission_type == "colab" and "html" in content_type and "json" not in content_type:
            result["remark"] = "not_downloadable"
        elif submission_type == "drive" and content_len < 100 and "html" in content_type:
            result["remark"] = "not_downloadable"
        else:
            result["valid"] = True
            result["validation_status"] = "valid"
            result["remark"] = "link_reachable_and_downloadable"
    except Exception as exc:
        result["remark"] = f"network_error: {exc}"
    state["validation_result"] = result
    return state
