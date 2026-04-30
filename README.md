# Auto Evaluator

Auto Evaluator is a production-style grading pipeline that evaluates student assignment submissions from an input Excel workbook and generates a structured output report.

It supports:
- Rubric generation from assignment PDF
- Submission link validation
- Content extraction from supported sources
- LLM-assisted evaluation with heuristic fallback
- Late penalty calculations
- Optional plagiarism checks
- Multi-sheet Excel reporting for summary and detailed breakdown

## Table of Contents
- Overview
- Features
- Architecture
- Project Structure
- Input Workbook Format
- Output Workbook Format
- Prerequisites
- Installation
- Configuration
- Usage (CLI)
- Usage (Web UI)
- Evaluation Rules
- Plagiarism Behavior
- Troubleshooting
- Testing
- Security and Data Handling
- Roadmap Suggestions

## Overview
The pipeline processes an assignment and student submission list in two phases:
1. Preprocessing phase: validate and extract content for all students.
2. Evaluation phase: score each student using generated rubric and penalties, then build reports.

This design improves consistency and enables student-to-student similarity checks when plagiarism checking is enabled.

## Features
- End-to-end grading from a single `.xlsx` input file.
- Configurable LLM provider (`openai` or `google`) with fallback mode.
- Automatic late-penalty policy with caps and reductions.
- Optional plagiarism detection controlled from UI checkbox.
- Clean summary report with pass/fail status and rubric-wise marks.
- Detailed criterion-level breakdown in a separate sheet.

## Architecture
Core workflow (high-level):
1. `rubric_agent`: Reads assignment PDF and generates rubric criteria.
2. `validator_agent`: Validates submission links and accessibility.
3. `extractor_agent`: Extracts text/code content from submissions.
4. `evaluator_agent`: Scores content against rubric, applies penalties, optionally checks plagiarism.
5. `report_agent`: Writes final Excel report sheets.

Entry points:
- CLI runner: `main.py`
- Web UI: `app.py`

## Project Structure
```text
Agent_E/
  app.py                          # Flask UI
  main.py                         # CLI + orchestration entry point
  requirements.txt
  .env.example
  templates/
    index.html                    # Upload form
    result.html                   # Result preview
  auto_evaluator/
    agents/
      rubric_agent.py
      validator_agent.py
      extractor_agent.py
      evaluator_agent.py
      report_agent.py
    orchestration/
      graph.py
    utils/
      config.py
      file_handlers.py
      llm_client.py
      heuristics.py
      late_penalty.py
      plagiarism.py
    state.py
  tests/
```

## Input Workbook Format
The input workbook must contain sheets expected by `read_input_excel`.

Typical required data includes:
- Assignment metadata (e.g., `assignment_name`, `pdf_link`, optional `deadline`)
- Student list with at least:
  - `student_name`
  - `submission_link`
  - `submission_timestamp` (used for late penalty)

If `pdf_link` is missing or empty, evaluation stops with an error.

## Output Workbook Format
The generated output file contains:

1. `summary`
- Student-level outcome and totals.
- Includes pass/fail status.
- `Remarks` behavior:
  - `Passed` for passed students.
  - Detailed failure reason for failed students.
- Rubric-wise columns are included as:
  - `Rubric - <Criterion Name>` with awarded score
  - `NA` for failed students.
- Plagiarism columns are included only when plagiarism check is enabled:
  - `Plagiarism Flag`
  - `Similarity Score`
  - `Matched With`

2. `detailed_breakdown`
- One row per student per criterion.
- Includes awarded marks, criterion weight, and justification.

3. `rubric`
- Generated rubric criteria with weight and description.

## Prerequisites
- Python 3.10+
- Windows, macOS, or Linux
- Internet access for LLM/API-backed evaluation (unless fallback-only flow is used)

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux, use:
```bash
source .venv/bin/activate
cp .env.example .env
```

## Configuration
Environment variables are read from `.env`.

Current variables from `.env.example`:
- `LLM_PROVIDER`: `openai` or `google`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GOOGLE_API_KEY`
- `GOOGLE_MODEL`
- `LLM_FORCE_FALLBACK`: `true|false`
- `DEFAULT_DEADLINE`: fallback deadline when input deadline missing
- `LATE_PENALTY_2_3_DAYS`
- `LATE_PENALTY_4_7_DAYS`
- `LATE_PENALTY_8_14_DAYS`
- `PLAGIARISM_THRESHOLD`
- `PASS_MARK`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_CONTENT_CHARS`

Runtime flag used by UI flow:
- `CHECK_PLAGIARISM`: set by web checkbox during each run (`true|false`)

## Usage (CLI)
Run with explicit input/output:
```bash
python main.py --input samples/input.xlsx --output samples/output.xlsx
```

Notes:
- CLI defaults to `CHECK_PLAGIARISM=true` unless you set it.
- To disable plagiarism in CLI:
```bash
set CHECK_PLAGIARISM=false
python main.py --input samples/input.xlsx --output samples/output.xlsx
```

## Usage (Web UI)
Start server:
```bash
python app.py
```

Open:
- `http://127.0.0.1:8501`

In UI:
1. Upload `.xlsx` input file.
2. Set output filename.
3. Choose `Use fallback mode` if you want non-LLM fallback behavior.
4. Enable `Run plagiarism check` only when needed.
5. Run evaluation and download output.

## Evaluation Rules
- Quality score is based on rubric criteria (target out of 15).
- Late policy contributes via penalty rules (from the 5-mark pool and additional reductions).
- Final score is capped according to late-submission logic in `late_penalty.py`.
- Invalid/unreadable submissions are preserved in reports and flagged for review.

## Plagiarism Behavior
When enabled:
- Similarity is calculated on normalized full extracted content.
- If similarity crosses threshold (`PLAGIARISM_THRESHOLD`), submission is flagged.

When disabled:
- No plagiarism computation is performed.
- Plagiarism-related columns are omitted from summary output.

## Troubleshooting
Common issues and fixes:

1. `Please upload a valid .xlsx file`
- Ensure file extension is `.xlsx`.

2. `The assignment sheet must include a non-empty pdf_link`
- Provide valid `pdf_link` in assignment metadata sheet.

3. API/provider errors
- Verify `OPENAI_API_KEY` or `GOOGLE_API_KEY`.
- Verify model names in `.env`.
- Use fallback mode as temporary workaround.

4. Empty or poor extraction
- Check submission link accessibility and permissions.
- Verify file format is supported by extractor.

5. Permission errors while running tests
- Run tests only from `tests/` scope if temp directories are restricted:
```bash
python -m pytest tests -q
```

## Testing
Run all tests:
```bash
python -m pytest tests -q
```

Expected result: all tests pass.

## Security and Data Handling
- API keys are loaded via environment variables; never commit secrets.
- Temporary run directories are created per evaluation in UI flow.
- Use private/self-hosted storage policies as required by your institution.

## Roadmap Suggestions
- Add authentication/role-based access for evaluators.
- Add richer plagiarism explainability (snippet-level evidence).
- Add async/background job queue for large batch runs.
- Export PDF summary dashboards.
- Add input template validator with user-friendly error localization.
