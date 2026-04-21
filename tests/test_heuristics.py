from auto_evaluator.utils.heuristics import generate_rubric_from_text, heuristic_evaluate_submission


def test_generate_rubric_from_text_uses_assignment_signals():
    rubric = generate_rubric_from_text(
        "Demo Assignment",
        "Evaluation criteria include correctness, code quality, naming, and documentation.",
    )
    assert rubric["max_score"] == 15
    assert len(rubric["criteria"]) >= 4


def test_heuristic_evaluate_submission_returns_non_zero_for_reasonable_code():
    rubric = {
        "max_score": 15,
        "criteria": [
            {"name": "Correctness of output", "weight": 7},
            {"name": "Code quality and structure", "weight": 4},
            {"name": "Naming conventions", "weight": 2},
            {"name": "Documentation and comments", "weight": 2},
        ],
    }
    content = """
    # FILE: solution.py
    import pandas as pd

    # summarize csv data
    def summarize_data(path):
        df = pd.read_csv(path)
        print(df.describe())
        return df
    """
    result = heuristic_evaluate_submission(rubric, content)
    assert result["total_score"] > 0
    assert len(result["scores_per_criterion"]) == 4
