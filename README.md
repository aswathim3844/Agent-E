# Auto Evaluator

This project evaluates student assignment submissions from an Excel file using a 5-agent workflow:

1. Rubric generation
2. Submission validation
3. Content extraction
4. Evaluation with plagiarism and late penalties
5. Report generation

Suspected or low-confidence cases are marked with `Needs Review` and `Review Reason` in the final Excel output.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your `OPENAI_API_KEY` or `GOOGLE_API_KEY` to `.env`.

## Run CLI

```bash
python main.py --input samples/input.xlsx --output samples/output.xlsx
```

## Run Flask UI

```bash
python app.py
```

Open `http://127.0.0.1:8501`.

## Validation policy

- Link checks are strict and type-aware.
- Unsupported or weak links are marked with machine-readable remarks such as:
  - `unsupported_link_type`
  - `private_or_auth_required`
  - `not_downloadable`
  - `empty_content`
  - `network_error`
  - `invalid_local_path`
- Policy is warn-and-continue: the run proceeds and flags records for review when needed.

## Plagiarism policy

- Plagiarism similarity is computed on normalized full text, including markdown and comments.
- Output now includes `Plagiarism Flag`, `Similarity Score`, and `Plagiarism Basis`.

## Output

The output Excel contains:

- `summary`
- `detailed_breakdown`
