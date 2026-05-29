import json
import re

from domain.ports import AIPort
from domain.value_objects import JDAnalysis

_SYSTEM = (
    "You are an expert ATS consultant and technical recruiter. "
    "Analyze job descriptions and extract structured requirements. "
    "Respond ONLY with valid JSON — no markdown, no explanation."
)

_PROMPT_TEMPLATE = """\
Analyze this job description and return a JSON object with these exact keys:

- role_title: the exact job title (string)
- seniority: one of ["junior", "mid", "senior", "lead", "director"] (string)
- required_keywords: 10-15 must-have skills or keywords (array of strings)
- preferred_keywords: 5-10 nice-to-have skills (array of strings)
- responsibilities: 5-8 key responsibilities extracted verbatim or paraphrased (array of strings)

Job Description:
{jd_text}
"""


class JDAnalyzer:
    def __init__(self, ai: AIPort) -> None:
        self._ai = ai

    def analyze(self, jd_text: str) -> JDAnalysis:
        prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text.strip())
        raw = self._ai.complete(prompt, system=_SYSTEM)
        data = _parse_json(raw)
        return JDAnalysis(
            role_title=data["role_title"],
            seniority=data["seniority"],
            required_keywords=tuple(data.get("required_keywords", [])),
            preferred_keywords=tuple(data.get("preferred_keywords", [])),
            responsibilities=tuple(data.get("responsibilities", [])),
            raw_jd=jd_text,
        )


def _parse_json(text: str) -> dict:
    """Extract JSON from model response, tolerating markdown code fences."""
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}\n---\n{clean}") from exc
