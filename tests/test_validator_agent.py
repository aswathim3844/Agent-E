from auto_evaluator.agents.validator_agent import validator_agent
from auto_evaluator.utils.config import AppConfig


class _Resp:
    def __init__(self, status_code=200, content=b"x", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"Content-Type": "application/octet-stream"}


def _state(link: str):
    return {
        "current_student": {"submission_link": link},
        "config": {"app_config": AppConfig()},
    }


def test_unsupported_link_type_is_warning_invalid():
    state = validator_agent(_state("https://example.com/file.exe"))
    assert state["validation_result"]["valid"] is False
    assert state["validation_result"]["validation_status"] == "warning_invalid"
    assert state["validation_result"]["remark"] == "unsupported_link_type"


def test_private_link_is_marked_private(monkeypatch):
    monkeypatch.setattr("auto_evaluator.agents.validator_agent.requests.get", lambda *a, **k: _Resp(status_code=403))
    state = validator_agent(_state("https://github.com/user/repo/blob/main/a.py"))
    assert state["validation_result"]["valid"] is False
    assert state["validation_result"]["remark"] == "private_or_auth_required"


def test_valid_local_path_passes():
    state = validator_agent(_state("samples\\asha_submission.ipynb"))
    assert state["validation_result"]["valid"] is True
    assert state["validation_result"]["remark"] == "valid_local_path"
