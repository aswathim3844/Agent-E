from __future__ import annotations

from datetime import datetime
from typing import Any

from auto_evaluator.utils.config import AppConfig


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError("Missing datetime value")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")


def calculate_days_late(submission_timestamp: Any, deadline: Any) -> int:
    if submission_timestamp in (None, "", float("nan")) or deadline in (None, "", float("nan")):
        return 0
    try:
        submitted_at = parse_datetime(submission_timestamp)
        deadline_at = parse_datetime(deadline)
    except Exception:
        return 0
    delta = submitted_at - deadline_at
    return max(0, delta.days)


def calculate_late_penalty(days_late: int, config: AppConfig) -> tuple[int, bool]:
    if days_late <= 1:
        return 0, False
    if 2 <= days_late <= 3:
        return config.late_penalty_2_3_days, False
    if 4 <= days_late <= 7:
        return config.late_penalty_4_7_days, False
    if 8 <= days_late <= 14:
        return config.late_penalty_8_14_days, False
    return config.late_penalty_8_14_days, True
