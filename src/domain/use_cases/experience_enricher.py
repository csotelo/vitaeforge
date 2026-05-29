import json
import re

from domain.ports import AIPort
from domain.models import CVData, Lang
from domain.value_objects import JDAnalysis

_SYSTEM = (
    "You are an expert CV writer and ATS consultant. "
    "You surface transferable skills by adding bridge bullets grounded in real experience. "
    "Respond ONLY with valid JSON — no markdown, no explanation."
)

_PROMPT = """\
Tailor a candidate's CV for a specific job. For each relevant experience entry generate ONE \
bridge bullet that:
1. Is strictly grounded in the existing bullets — no fabrication
2. Reframes the most relevant aspect using target-role language
3. Embeds JD keywords naturally (no stuffing)
4. Starts with a strong action verb and includes a measurable impact when possible
5. Is written in {lang}

Only include experiences that are actually relevant to the role — omit unrelated ones.

Return ONLY this JSON:
{{
  "enrichments": [
    {{"company": "<exact company name>", "start_date": "<start date as shown in Period>", "bridge_bullet": "<one sentence>"}},
    ...
  ]
}}

--- CANDIDATE EXPERIENCES ---
{experiences}

--- TARGET ROLE ---
Role: {role_title} ({seniority})
Required skills: {required_keywords}
Key responsibilities:
{responsibilities}
"""

_ONE_PAGE_PROMPT = """\
You are preparing a one-page CV. Analyze ALL the candidate's experiences \
and select the {max_entries} most relevant ones for the target role. For each selected experience, \
write ONE compact paragraph of exactly 2 sentences that:
1. Is strictly grounded in the existing bullets — no fabrication
2. First sentence: most ATS-impactful contribution with a strong action verb and measurable result
3. Second sentence: key skill or tool that directly maps to the target role
4. Embeds JD keywords naturally (no stuffing)
5. Is written in {lang} as flowing prose — no bullets, no line breaks

Maximum 45 words total. Be concise — every word must earn its place.

Rank selections by ATS relevance to the target role. Return ONLY this JSON:
{{
  "enrichments": [
    {{
      "company": "<exact company name>",
      "start_date": "<only the start date, e.g. 2025-04>",
      "ats_score": <0-100 relevance score>,
      "paragraph": "<2-sentence paragraph, max 45 words>"
    }},
    ...
  ]
}}

--- CANDIDATE EXPERIENCES ---
{experiences}

--- TARGET ROLE ---
Role: {role_title} ({seniority})
Required skills: {required_keywords}
Key responsibilities:
{responsibilities}
"""


class ExperienceEnricher:
    def __init__(self, ai: AIPort) -> None:
        self._ai = ai

    def enrich(self, cv: CVData, jd: JDAnalysis, lang: Lang) -> dict[str, str]:
        """Returns {(company, start_date): bridge_bullet} for relevant experiences."""
        prompt = _PROMPT.format(
            lang=lang.value,
            experiences=_format_experiences(cv, lang),
            role_title=jd.role_title,
            seniority=jd.seniority,
            required_keywords=", ".join(jd.required_keywords),
            responsibilities="\n".join(f"- {r}" for r in jd.responsibilities),
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        data = _parse_json(raw)
        return {(e["company"], e.get("start_date", "")): e["bridge_bullet"] for e in data.get("enrichments", [])}

    def enrich_one_page(
        self, cv: CVData, jd: JDAnalysis, lang: Lang, max_entries: int = 8
    ) -> tuple[list[str], dict[str, str]]:
        """Ranks experiences by ATS relevance and returns per-role summary paragraphs.

        Returns (ranked_companies, {(company, start_date): paragraph}) ordered most to least relevant.
        """
        prompt = _ONE_PAGE_PROMPT.format(
            max_entries=max_entries,
            lang=lang.value,
            experiences=_format_experiences(cv, lang),
            role_title=jd.role_title,
            seniority=jd.seniority,
            required_keywords=", ".join(jd.required_keywords),
            responsibilities="\n".join(f"- {r}" for r in jd.responsibilities),
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        data = _parse_json(raw)
        items = sorted(
            data.get("enrichments", []),
            key=lambda e: e.get("ats_score", 0),
            reverse=True,
        )
        ranked = [(e["company"], e.get("start_date", "")) for e in items]
        paragraphs = {(e["company"], e.get("start_date", "")): e["paragraph"] for e in items}
        return ranked, paragraphs


def _format_experiences(cv: CVData, lang: Lang) -> str:
    lines = []
    for exp in cv.experience:
        lines.append(f"Company: {exp.company}")
        lines.append(f"Role: {exp.role.get(lang)}")
        lines.append(f"Period: {exp.start_date} – {exp.end_date}")
        if exp.bullets:
            lines.append("Bullets:")
            for b in exp.bullets:
                lines.append(f"  - {b.get(lang)}")
        if exp.aptitudes:
            lines.append(f"Skills used: {', '.join(exp.aptitudes)}")
        lines.append("")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}\n---\n{clean}") from exc
