from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pandas as pd
from flask import Flask, abort, redirect, render_template, request, send_file, url_for

from auto_evaluator.utils.file_handlers import read_input_excel
from main import run


app = Flask(__name__)
_JOBS: dict[str, dict[str, str]] = {}


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/evaluate")
def evaluate():
    uploaded_file = request.files.get("input_file")
    if not uploaded_file or not uploaded_file.filename.lower().endswith(".xlsx"):
        return render_template("index.html", error="Please upload a valid .xlsx file.")

    fallback_mode = request.form.get("fallback_mode") == "on"
    check_plagiarism = request.form.get("check_plagiarism") == "on"
    output_name = request.form.get("output_name", "output.xlsx").strip() or "output.xlsx"
    if not output_name.lower().endswith(".xlsx"):
        output_name += ".xlsx"

    temp_run_dir = Path(tempfile.mkdtemp(prefix="auto_eval_run_"))
    input_path = temp_run_dir / uploaded_file.filename
    output_path = temp_run_dir / output_name
    input_path.write_bytes(uploaded_file.read())

    try:
        assignment_preview, students_preview = read_input_excel(str(input_path))
        os.environ["LLM_FORCE_FALLBACK"] = "true" if fallback_mode else "false"
        os.environ["CHECK_PLAGIARISM"] = "true" if check_plagiarism else "false"
        final_state = run(str(input_path), str(output_path))
        summary_df = pd.read_excel(output_path, sheet_name="summary")
        rubric = final_state.get("rubric", {})

        job_id = str(uuid.uuid4())
        _JOBS[job_id] = {
            "output_path": str(output_path),
            "output_name": output_name,
            "rubric_json": json.dumps(rubric, indent=2),
            "temp_dir": str(temp_run_dir),
        }

        return render_template(
            "result.html",
            assignment_name=assignment_preview.get("assignment_name", ""),
            pdf_link=assignment_preview.get("pdf_link", ""),
            deadline=assignment_preview.get("deadline", ""),
            students_count=len(students_preview),
            summary_columns=list(summary_df.columns),
            summary_rows=summary_df.fillna("").to_dict(orient="records"),
            rubric=rubric,
            rubric_json=_JOBS[job_id]["rubric_json"],
            download_url=url_for("download_output", job_id=job_id),
        )
    except Exception as exc:
        shutil.rmtree(temp_run_dir, ignore_errors=True)
        return render_template("index.html", error=f"Evaluation failed: {exc}")


@app.get("/download/<job_id>")
def download_output(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        abort(404)
    output_path = Path(job["output_path"])
    if not output_path.exists():
        abort(404)
    return send_file(output_path, as_attachment=True, download_name=job["output_name"])


@app.get("/rubric/<job_id>")
def download_rubric(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        abort(404)
    tmp = Path(tempfile.mkdtemp(prefix="auto_eval_rubric_")) / "rubric.json"
    tmp.write_text(job["rubric_json"], encoding="utf-8")
    return send_file(tmp, as_attachment=True, download_name="rubric.json")


@app.get("/reset")
def reset():
    for job in list(_JOBS.values()):
        shutil.rmtree(job.get("temp_dir", ""), ignore_errors=True)
    _JOBS.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8501, debug=False)
