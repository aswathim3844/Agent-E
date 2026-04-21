from auto_evaluator.utils.config import AppConfig
from auto_evaluator.utils.late_penalty import calculate_late_penalty
from auto_evaluator.utils.plagiarism import normalize_content, similarity_score


def test_late_penalty_bands():
    config = AppConfig()
    assert calculate_late_penalty(0, config) == (0, False)
    assert calculate_late_penalty(1, config) == (0, False)
    assert calculate_late_penalty(2, config) == (1, False)
    assert calculate_late_penalty(5, config) == (3, False)
    assert calculate_late_penalty(10, config) == (5, False)
    assert calculate_late_penalty(20, config) == (5, True)


def test_plagiarism_normalization_and_similarity():
    left = """
    # comment
    def add(a, b):
        return a + b
    """
    right = """
    def add(a,b):
        return a+b  # same logic
    """
    normalized_left = normalize_content(left)
    normalized_right = normalize_content(right)
    assert normalized_left == normalized_right
    assert similarity_score(normalized_left, normalized_right) == 1.0
