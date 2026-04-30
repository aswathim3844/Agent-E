from pathlib import Path

import pandas as pd

from auto_evaluator.utils.file_handlers import detect_submission_type, extract_submission_content


def test_detect_submission_type_for_local_excel():
    assert detect_submission_type("samples\\data.xlsx") == "tabular"


def test_detect_submission_type_for_remote_excel():
    assert detect_submission_type("https://example.com/data.xlsx") == "tabular"


def test_extract_submission_content_for_local_excel():
    excel_path = Path("samples") / "test_submission_generated.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_excel(writer, index=False, sheet_name="Sheet1")

    try:
        content, metadata = extract_submission_content(str(excel_path), "tabular")
        assert "SHEET: Sheet1" in content
        assert "a,b" in content
        assert metadata["files_read"] == 1
        assert metadata["rows"] == 2
    finally:
        excel_path.unlink(missing_ok=True)


def test_detect_submission_type_for_github_blob_ipynb():
    url = "https://github.com/org/repo/blob/main/notebook.ipynb"
    assert detect_submission_type(url) == "github_file"
