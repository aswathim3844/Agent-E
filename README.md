<<<<<<< HEAD
# Agent-E
=======
# Auto Evaluator

This project evaluates student assignment submissions from an Excel file using a 5-agent workflow:

1. Rubric generation
2. Submission validation
3. Content extraction
4. Evaluation with plagiarism and late penalties
5. Report generation

Human intervention is intentionally removed. Suspected or low-confidence cases are marked with `Needs Review` and `Review Reason` in the final Excel output.

## Project structure

```text
auto_evaluator/
  agents/
  orchestration/
  utils/
main.py
app.py
requirements.txt
.env.example
samples/
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your `OPENAI_API_KEY` or `GOOGLE_API_KEY` to `.env`.

## Input format

The input Excel file needs two sheets:

- `assignment`
- `submissions`

Required columns:

`assignment` sheet:
- `assignment_name`
- `pdf_link`
- `deadline`

`submissions` sheet:
- `student_name`
- `submission_link`
- `submission_timestamp`

## Run

```bash
python samples/generate_sample_input.py
```

For a local dry run without calling an external LLM, set `LLM_FORCE_FALLBACK=true` in `.env`, then run:

```bash
python main.py --input samples/input.xlsx --output samples/output.xlsx
```

To use the browser upload frontend:

```bash
streamlit run app.py
```

## Output

The output Excel file includes:

- `summary`
- `detailed_breakdown`

The `summary` sheet includes total marks, quality score, plagiarism flag, late penalties, and review flags.

## Frontend

The Streamlit app lets you upload an Excel file from your computer, run the evaluator, and download the output without typing file paths.

## Notes

- Public GitHub repositories and direct zip/notebook URLs are the most reliable sources for v1.
- Local file paths are also supported for PDFs, notebooks, zip files, and folders of source files, which makes local testing much easier.
- Google Drive and Colab links work best when they are public and downloadable. The validator now attempts to convert common Drive and Colab share links into direct download URLs.
- Plagiarism detection uses normalized exact-copy similarity within the same batch.
- If the LLM fails, the system falls back to zero-score rubric entries and records that in remarks.
- You can set `LLM_FORCE_FALLBACK=true` to test the workflow without calling an external model.
>>>>>>> cc84891 (Agent_E)
