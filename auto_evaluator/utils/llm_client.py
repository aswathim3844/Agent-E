from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI

from auto_evaluator.utils.config import AppConfig


LOGGER = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._openai = OpenAI(api_key=config.openai_api_key) if config.openai_api_key else None
        self._gemini_ready = bool(config.google_api_key)

    def _call_openai_json(self, prompt: str) -> dict[str, Any]:
        if not self._openai:
            raise ValueError("OPENAI_API_KEY is not configured")
        response = self._openai.responses.create(
            model=self.config.openai_model,
            input=prompt,
            temperature=0,
        )
        text = response.output_text
        return json.loads(text)

    def _call_gemini_json(self, prompt: str) -> dict[str, Any]:
        if not self._gemini_ready:
            raise ValueError("GOOGLE_API_KEY is not configured")
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "google.genai is not installed. Install the google-genai package to use Gemini."
            ) from exc
        client = genai.Client(api_key=self.config.google_api_key)
        model = client.models.generate_content(
            model=self.config.google_model,
            contents=prompt,
        )
        return json.loads(model.text)

    def call_json(self, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if self.config.llm_force_fallback:
            return fallback
        retries = 3
        for attempt in range(retries):
            try:
                if self.config.llm_provider.lower() == "openai":
                    return self._call_openai_json(prompt)
                if self.config.llm_provider.lower() in {"google", "gemini"}:
                    return self._call_gemini_json(prompt)
                raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")
            except Exception as exc:
                LOGGER.warning("LLM call failed on attempt %s: %s", attempt + 1, exc)
                time.sleep(2**attempt)
        return fallback


def build_rubric_prompt(assignment_name: str, pdf_text: str) -> str:
    return f"""
You are generating a grading rubric for a programming assignment.
Return strict JSON only with keys: max_score, criteria.
The criteria array must contain objects with keys: name, weight, description.
Weights must sum exactly to 15.
Do not copy any external rubric text verbatim.
Use the following as style reference only (paraphrase and adapt to assignment context):
- Initial dataset understanding and summary statistics
- Redundancy/duplicate checks
- Missing value handling strategy
- Feature scaling correctness (exclude target from scaling)
- Categorical encoding method selection
- Outlier detection and treatment
- Proper train/test split and target separation
Prefer 5-7 criteria with practical, measurable descriptions.

Assignment name: {assignment_name}
Assignment text:
{pdf_text[:12000]}
""".strip()


def build_evaluation_prompt(rubric: dict[str, Any], extracted_content: str) -> str:
    return f"""
You are grading a student programming submission.
Return strict JSON only with keys:
scores_per_criterion, total_score, remarks, confidence.
scores_per_criterion must be an array of objects with keys:
name, awarded, weight, justification.
total_score must be out of 15.
confidence must be a float between 0 and 1.

Rubric:
{json.dumps(rubric, indent=2)}

Submission content:
{extracted_content[:25000]}
""".strip()
