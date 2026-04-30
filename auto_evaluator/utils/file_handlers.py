from __future__ import annotations

import io
import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from difflib import SequenceMatcher

import fitz
import nbformat
import pandas as pd
import requests
from git import Repo


LOGGER = logging.getLogger(__name__)

TEXT_EXTENSIONS = {
    ".py",
    ".ipynb",
    ".java",
    ".cpp",
    ".c",
    ".js",
    ".ts",
    ".txt",
    ".md",
    ".html",
    ".css",
    ".sql",
}
TABULAR_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _best_match(target: str, candidates: list[str], threshold: float = 0.72) -> str:
    if not candidates:
        raise ValueError(f"No candidates available for {target}")
    normalized_target = _normalize_name(target)
    scored = [
        (SequenceMatcher(None, normalized_target, _normalize_name(candidate)).ratio(), candidate)
        for candidate in candidates
    ]
    scored.sort(reverse=True)
    score, candidate = scored[0]
    if score < threshold:
        raise ValueError(f"Could not find a close match for '{target}'")
    return candidate


def _resolve_sheet_name(sheet_names: list[str], target: str) -> str:
    normalized_lookup = {_normalize_name(name): name for name in sheet_names}
    normalized_target = _normalize_name(target)
    if normalized_target in normalized_lookup:
        return normalized_lookup[normalized_target]
    return _best_match(target, sheet_names)


def _resolve_columns(df: pd.DataFrame, required: dict[str, list[str]]) -> pd.DataFrame:
    renamed = {}
    existing = list(df.columns)
    used_columns: set[str] = set()
    for canonical, aliases in required.items():
        if canonical in df.columns:
            used_columns.add(canonical)
            continue
        match = None
        normalized_aliases = {_normalize_name(alias) for alias in aliases + [canonical]}

        # Prefer exact normalized matches from currently unused columns.
        for col in existing:
            if col in used_columns:
                continue
            if _normalize_name(col) in normalized_aliases:
                match = col
                break

        if match is None:
            all_candidates = [col for col in existing if col not in used_columns]
            for alias in aliases:
                try:
                    match = _best_match(alias, all_candidates)
                    break
                except ValueError:
                    continue
        if match is None:
            raise ValueError(f"Missing required column: {canonical}")
        renamed[match] = canonical
        used_columns.add(match)
    return df.rename(columns=renamed)


def read_input_excel(input_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    workbook = pd.ExcelFile(input_path)
    assignment_sheet = _resolve_sheet_name(workbook.sheet_names, "assignment")
    submissions_sheet = _resolve_sheet_name(workbook.sheet_names, "submissions")
    assignment_df = pd.read_excel(input_path, sheet_name=assignment_sheet)
    submissions_df = pd.read_excel(input_path, sheet_name=submissions_sheet)
    assignment_df = _resolve_columns(
        assignment_df,
        {
            "assignment_name": ["assignment name", "assignment", "title", "name"],
            "pdf_link": ["pdf link", "pdf", "assignment pdf", "instructions"],
            "deadline": ["due date", "deadline date", "submission deadline", "due"],
        },
    )
    submissions_df = _resolve_columns(
        submissions_df,
        {
            "student_name": ["student name", "name", "student", "learner"],
            "submission_link": ["submission link", "link", "submission", "work link"],
            "submission_timestamp": [
                "submission time",
                "timestamp",
                "submitted at",
                "received time",
                "date submitted",
                "submission_timestamp(date(yyyy-mm-dd) (hh:mm:ss)",
            ],
        },
    )
    assignment = assignment_df.iloc[0].to_dict()
    students = submissions_df.to_dict(orient="records")
    return assignment, students


def extract_pdf_text(pdf_source: str, timeout_seconds: int = 30) -> str:
    data: bytes
    if is_url(pdf_source):
        response = requests.get(pdf_source, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.content
    else:
        data = Path(pdf_source).read_bytes()
    text_chunks: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_chunks.append(page.get_text("text"))
    return "\n".join(text_chunks).strip()


def detect_submission_type(url: str) -> str:
    lowered = (url or "").lower()
    if not is_url(lowered):
        suffix = Path(url).suffix.lower()
        if suffix == ".zip":
            return "zip"
        if suffix in TABULAR_EXTENSIONS:
            return "tabular"
        if suffix == ".ipynb":
            return "local_text"
        if suffix in TEXT_EXTENSIONS:
            return "local_text"
        if Path(url).is_dir():
            return "local_dir"
    if "github.com" in lowered:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix.lower()
        if "/blob/" in lowered and (suffix in TEXT_EXTENSIONS or suffix in TABULAR_EXTENSIONS):
            return "github_file"
        return "github"
    if "colab.research.google.com" in lowered or lowered.endswith(".ipynb") or "/blob/" in lowered:
        return "colab"
    if "drive.google.com" in lowered:
        return "drive"
    if lowered.endswith(".zip"):
        return "zip"
    if any(lowered.endswith(ext) for ext in TABULAR_EXTENSIONS):
        return "tabular"
    return "other"


def extract_tabular_content(raw_bytes: bytes, extension: str) -> tuple[str, dict[str, Any]]:
    suffix = (extension or "").lower()
    if suffix == ".csv":
        df = pd.read_csv(io.BytesIO(raw_bytes))
        return df.to_csv(index=False), {"files_read": 1, "rows": int(df.shape[0]), "columns": int(df.shape[1])}
    df_map = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
    parts: list[str] = []
    total_rows = 0
    total_columns = 0
    for sheet_name, df in df_map.items():
        total_rows += int(df.shape[0])
        total_columns = max(total_columns, int(df.shape[1]))
        parts.append(f"# SHEET: {sheet_name}")
        if df.empty:
            parts.append("(empty sheet)")
        else:
            parts.append(df.to_csv(index=False))
    return "\n\n".join(parts).strip(), {
        "files_read": 1,
        "sheet_count": len(df_map),
        "rows": total_rows,
        "columns": total_columns,
    }


def fetch_url_content(url: str, timeout_seconds: int = 30) -> bytes:
    response = requests.get(
        url,
        timeout=timeout_seconds,
        allow_redirects=True,
        headers={"User-Agent": "auto-evaluator/1.0"},
    )
    response.raise_for_status()
    return response.content


def read_local_text_file(path: str) -> tuple[str, dict[str, Any]]:
    file_path = Path(path)
    raw_bytes = file_path.read_bytes()
    if file_path.suffix.lower() == ".ipynb":
        return extract_notebook_cells(raw_bytes), {"files_read": 1}
    return raw_bytes.decode("utf-8", errors="ignore"), {"files_read": 1}


def extract_local_directory_content(path: str) -> tuple[str, dict[str, Any]]:
    base = Path(path)
    parts: list[str] = []
    file_count = 0
    for file_path in base.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        file_count += 1
        raw_bytes = file_path.read_bytes()
        rel = file_path.relative_to(base).as_posix()
        if file_path.suffix.lower() == ".ipynb":
            parts.append(f"\n# FILE: {rel}\n{extract_notebook_cells(raw_bytes)}")
        else:
            parts.append(f"\n# FILE: {rel}\n{raw_bytes.decode('utf-8', errors='ignore')}")
    return "\n".join(parts).strip(), {"files_read": file_count}


def build_raw_github_url(url: str) -> str:
    if "raw.githubusercontent.com" in url:
        return url
    if "github.com" in url and "/blob/" in url:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        owner, repo, _, branch, *rest = path.split("/")
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{'/'.join(rest)}"
    return url


def build_colab_download_url(url: str) -> str:
    if url.lower().endswith(".ipynb"):
        return build_raw_github_url(url)
    if "colab.research.google.com" in url:
        if "/github/" in url:
            suffix = url.split("/github/", 1)[1]
            return f"https://raw.githubusercontent.com/{suffix.replace('/blob/', '/')}"
        if "drive/" in url:
            file_id_match = re.search(r"/d/([A-Za-z0-9_-]+)", url)
            if file_id_match:
                file_id = file_id_match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def build_drive_download_url(url: str) -> str:
    if "uc?export=download" in url:
        return url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "id" in query:
        return f"https://drive.google.com/uc?export=download&id={query['id'][0]}"
    file_id_match = re.search(r"/d/([A-Za-z0-9_-]+)", url)
    if file_id_match:
        return f"https://drive.google.com/uc?export=download&id={file_id_match.group(1)}"
    return url


def extract_notebook_cells(raw_bytes: bytes) -> str:
    notebook = nbformat.read(io.StringIO(raw_bytes.decode("utf-8", errors="ignore")), as_version=4)
    cells: list[str] = []
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cells.append(cell.source)
    return "\n\n".join(cells).strip()


def extract_zip_content(raw_bytes: bytes) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    file_count = 0
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        for name in archive.namelist():
            suffix = Path(name).suffix.lower()
            if suffix not in TEXT_EXTENSIONS:
                continue
            file_count += 1
            file_data = archive.read(name)
            if suffix == ".ipynb":
                parts.append(f"\n# FILE: {name}\n{extract_notebook_cells(file_data)}")
            else:
                parts.append(f"\n# FILE: {name}\n{file_data.decode('utf-8', errors='ignore')}")
    return "\n".join(parts).strip(), {"files_read": file_count}


def extract_github_repo_content(repo_url: str) -> tuple[str, dict[str, Any]]:
    temp_dir = tempfile.mkdtemp(prefix="auto_eval_repo_")
    try:
        Repo.clone_from(repo_url, temp_dir, depth=1)
        parts: list[str] = []
        file_count = 0
        for path in Path(temp_dir).rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            file_count += 1
            raw_bytes = path.read_bytes()
            rel = path.relative_to(temp_dir).as_posix()
            if path.suffix.lower() == ".ipynb":
                parts.append(f"\n# FILE: {rel}\n{extract_notebook_cells(raw_bytes)}")
            else:
                parts.append(f"\n# FILE: {rel}\n{raw_bytes.decode('utf-8', errors='ignore')}")
        return "\n".join(parts).strip(), {"files_read": file_count}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def extract_submission_content(url: str, submission_type: str, timeout_seconds: int = 30) -> tuple[str, dict[str, Any]]:
    try:
        suffix = Path(urlparse(url).path if is_url(url) else url).suffix.lower()
        if submission_type == "local_text":
            return read_local_text_file(url)
        if submission_type == "local_dir":
            return extract_local_directory_content(url)
        if submission_type == "tabular" and not is_url(url):
            return extract_tabular_content(Path(url).read_bytes(), suffix)
        if submission_type == "zip" and not is_url(url):
            return extract_zip_content(Path(url).read_bytes())
        if submission_type == "github":
            return extract_github_repo_content(url)
        if submission_type == "github_file":
            raw_url = build_raw_github_url(url)
            data = fetch_url_content(raw_url, timeout_seconds)
            if suffix == ".ipynb":
                return extract_notebook_cells(data), {"files_read": 1}
            if suffix in TABULAR_EXTENSIONS:
                return extract_tabular_content(data, suffix)
            return data.decode("utf-8", errors="ignore"), {"files_read": 1}
        if submission_type == "tabular":
            return extract_tabular_content(fetch_url_content(url, timeout_seconds), suffix)
        if submission_type == "zip":
            return extract_zip_content(fetch_url_content(url, timeout_seconds))
        if submission_type == "colab":
            data = fetch_url_content(build_colab_download_url(url), timeout_seconds)
            return extract_notebook_cells(data), {"files_read": 1}
        if submission_type == "drive":
            download_url = build_drive_download_url(url)
            data = fetch_url_content(download_url, timeout_seconds)
            if url.lower().endswith(".zip"):
                return extract_zip_content(data)
            if url.lower().endswith(".ipynb"):
                return extract_notebook_cells(data), {"files_read": 1}
            return data.decode("utf-8", errors="ignore"), {"files_read": 1}
    except Exception as exc:
        LOGGER.exception("Content extraction failed for %s", url)
        return "", {"error": str(exc), "files_read": 0}
    return "", {"error": f"Unsupported submission type: {submission_type}", "files_read": 0}
