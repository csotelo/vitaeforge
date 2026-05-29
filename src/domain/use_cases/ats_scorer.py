import json
import re

from domain.ports import AIPort
from domain.models import CVData, Lang
from domain.value_objects import JDAnalysis, ATSResult

_SYSTEM = (
    "You are an expert ATS consultant. "
    "Generate tailored CV content that maximizes ATS scores while remaining authentic. "
    "Respond ONLY with valid JSON — no markdown, no explanation."
)

_PROMPT_TEMPLATE = """\
Given the candidate's CV facts and the job requirements below, generate a JSON object with:

- headline: one-line professional title tailored to this role (under 120 chars, in {lang})
- summary: 3-4 sentence career summary tailored to the role (in {lang})
- ats_keywords: list of 15-20 keywords to feature prominently (strings)
- score: integer 0-100 estimating current ATS match before tailoring
- matched_keywords: keywords present in both the CV and the JD (strings)
- missing_keywords: important JD keywords not found in the CV (strings)

Language for headline and summary: {lang}

--- CV FACTS ---
{cv_facts}

--- JOB REQUIREMENTS ---
Role: {role_title} ({seniority})
Required keywords: {required_keywords}
Preferred keywords: {preferred_keywords}
Key responsibilities:
{responsibilities}
"""


class ATSScorer:
    def __init__(self, ai: AIPort) -> None:
        self._ai = ai

    def score(self, cv: CVData, jd: JDAnalysis, lang: Lang) -> ATSResult:
        prompt = _PROMPT_TEMPLATE.format(
            lang=lang.value,
            cv_facts=_summarize_cv(cv),
            role_title=jd.role_title,
            seniority=jd.seniority,
            required_keywords=", ".join(jd.required_keywords),
            preferred_keywords=", ".join(jd.preferred_keywords),
            responsibilities="\n".join(f"- {r}" for r in jd.responsibilities),
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        data = _parse_json(raw)
        return ATSResult(
            headline=data["headline"],
            summary=data["summary"],
            ats_keywords=tuple(data.get("ats_keywords", [])),
            score=int(data.get("score", 0)),
            matched_keywords=tuple(data.get("matched_keywords", [])),
            missing_keywords=tuple(data.get("missing_keywords", [])),
        )


def _summarize_cv(cv: CVData) -> str:
    """Convert CVData to readable text for the AI — facts only, no YAML noise."""
    lines = [
        f"Name: {cv.name} {cv.lastname}",
        f"Location: {cv.location.en}",
        "",
        "Experience:",
    ]
    for exp in cv.experience:
        lines.append(
            f"  - {exp.role.en} at {exp.company} "
            f"({exp.start_date} – {exp.end_date})"
        )
        if exp.aptitudes:
            lines.append(f"    Skills used: {', '.join(exp.aptitudes)}")

    lines.append("")
    lines.append("Skills: " + ", ".join(s.skill for s in cv.skills))

    if cv.education:
        lines.append("")
        lines.append("Education:")
        for edu in cv.education:
            lines.append(f"  - {edu.degree.en}, {edu.institution} ({edu.end_date})")

    if cv.languages:
        lines.append("")
        lines.append("Languages: " + ", ".join(
            f"{l.name.en} ({l.level.en})" for l in cv.languages
        ))

    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}\n---\n{clean}") from exc
