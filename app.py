from __future__ import annotations

import os
import tempfile
import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from auto_evaluator.utils.file_handlers import read_input_excel
from main import run


st.set_page_config(page_title="Auto Evaluator", layout="wide")

st.title("Auto Evaluator")
st.write("Upload an input Excel file, run the evaluator, and preview the output.")

with st.sidebar:
    st.header("Settings")
    fallback_mode = st.checkbox("Use fallback mode", value=True)
    output_name = st.text_input("Output file name", value="output.xlsx")

uploaded_file = st.file_uploader("Upload input Excel file", type=["xlsx"])

if uploaded_file:
    st.success(f"Loaded: {uploaded_file.name}")
    st.caption("The app will save your file locally, run the evaluator, and build an output Excel file.")

    temp_preview_dir = Path(tempfile.mkdtemp(prefix="auto_eval_preview_"))
    preview_path = temp_preview_dir / uploaded_file.name
    preview_path.write_bytes(uploaded_file.getvalue())
    try:
        assignment_preview, students_preview = read_input_excel(str(preview_path))
        st.write("File preview")
        st.json(
            {
                "assignment_name": assignment_preview.get("assignment_name", ""),
                "pdf_link": assignment_preview.get("pdf_link", ""),
                "deadline": assignment_preview.get("deadline", ""),
                "students_count": len(students_preview),
            }
        )
    except Exception as exc:
        st.error(
            "The app could not understand this file yet. "
            "It will still try to use close matches for sheet and column names, but the workbook needs at least one assignment sheet and one submissions sheet."
        )
        st.caption(f"Template check failed: {exc}")
        shutil.rmtree(temp_preview_dir, ignore_errors=True)
        st.stop()
    finally:
        shutil.rmtree(temp_preview_dir, ignore_errors=True)

    if st.button("Run Evaluation", type="primary"):
        temp_run_dir = Path(tempfile.mkdtemp(prefix="auto_eval_run_"))
        input_path = temp_run_dir / uploaded_file.name
        output_path = temp_run_dir / output_name

        try:
            input_path.write_bytes(uploaded_file.getvalue())
            os.environ["LLM_FORCE_FALLBACK"] = "true" if fallback_mode else "false"

            progress = st.progress(0, text="Starting evaluation...")
            try:
                progress.progress(20, text="Saved input file")
                with st.spinner("Running evaluator..."):
                    run(str(input_path), str(output_path))
                progress.progress(80, text="Building preview")
                summary_df = pd.read_excel(output_path, sheet_name="summary")
                progress.progress(100, text="Done")
                st.success("Evaluation complete.")
                st.download_button(
                    "Download output Excel",
                    data=output_path.read_bytes(),
                    file_name=output_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.subheader("Summary Preview")
                st.dataframe(summary_df, use_container_width=True)
            except Exception as exc:
                progress.empty()
                st.error(f"Evaluation failed: {exc}")
        finally:
            shutil.rmtree(temp_run_dir, ignore_errors=True)
else:
    st.info("Choose an `.xlsx` file to start.")
