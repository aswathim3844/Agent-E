from __future__ import annotations

from pathlib import Path
import zipfile

import fitz
import pandas as pd


def create_assignment_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Python Data Analysis Assignment\n\n"
        "Build a program that loads a CSV file, computes summary statistics, "
        "and writes the cleaned dataset plus a short report.\n\n"
        "Evaluation criteria:\n"
        "1. Correctness of output\n"
        "2. Code quality and structure\n"
        "3. Naming conventions\n"
        "4. Documentation and comments\n"
    )
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


def create_zip_submission(path: Path) -> None:
    temp_py = path.with_suffix(".py")
    temp_py.write_text(
        "import pandas as pd\n\n"
        "def summarize(path):\n"
        "    df = pd.read_csv(path)\n"
        "    print(df.describe())\n"
        "    return df\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.write(temp_py, arcname="solution.py")
    temp_py.unlink(missing_ok=True)


def create_notebook_submission(path: Path) -> None:
    path.write_text(
        '{'
        '"cells":[{"cell_type":"code","execution_count":null,"id":"cell-1","metadata":{},'
        '"outputs":[],"source":["import pandas as pd\\n","print(\\"hello\\")"]}],'
        '"metadata":{},"nbformat":4,"nbformat_minor":5'
        '}',
        encoding="utf-8",
    )


def main() -> None:
    samples_dir = Path(__file__).resolve().parent
    pdf_path = samples_dir / "assignment.pdf"
    zip_path = samples_dir / "rahul_submission.zip"
    notebook_path = samples_dir / "asha_submission.ipynb"

    create_assignment_pdf(pdf_path)
    create_zip_submission(zip_path)
    create_notebook_submission(notebook_path)

    assignment = pd.DataFrame(
        [
            {
                "assignment_name": "Python Data Analysis Assignment",
                "pdf_link": str(pdf_path),
                "deadline": "2026-04-15 23:59:59",
            }
        ]
    )
    submissions = pd.DataFrame(
        [
            {
                "student_name": "Asha Kumar",
                "submission_link": str(notebook_path),
                "submission_timestamp": "2026-04-15 20:00:00",
            },
            {
                "student_name": "Rahul Verma",
                "submission_link": str(zip_path),
                "submission_timestamp": "2026-04-17 10:30:00",
            },
        ]
    )
    output = samples_dir / "input.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        assignment.to_excel(writer, sheet_name="assignment", index=False)
        submissions.to_excel(writer, sheet_name="submissions", index=False)


if __name__ == "__main__":
    main()
