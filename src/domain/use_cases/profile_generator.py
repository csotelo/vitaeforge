import json
import re
from datetime import date

from domain.ports import AIPort
from domain.models import CVData, Lang

_LANG_LABEL = {Lang.EN: "English", Lang.ES: "Spanish"}

_SYSTEM = (
    "You are an expert CV writer and personal branding consultant. "
    "You write compelling, ATS-friendly profile summaries grounded strictly in real experience. "
    "CRITICAL RULE: Use ONLY information explicitly present in the candidate data provided. "
    "Do NOT invent, estimate, extrapolate, or assume any fact not stated in the data. "
    "If a specific detail is missing, omit it — never fill the gap with invented content. "
    "Respond ONLY with valid JSON — no markdown, no explanation."
)

_NEW_PROFILE_PROMPT = """\
⚠ GROUNDING RULE (read before anything else): Every fact in the summary MUST come \
from the candidate data below. Do NOT invent years, achievements, tools, or roles. \
If a detail is not in the data, omit it entirely.

You are a senior recruiter and CV specialist. Given a target role and a candidate's \
background, produce everything needed to create a professional CV profile.

1. List the top 15 ATS keywords recruiters search for in this role (tools, skills, methodologies)
2. Choose the most relevant skill_tags from this fixed list: \
[software_engineer, data_engineer, technical_product_owner, all]
3. Write a concise headline (8-12 words) in English and Spanish
4. Write a 3-4 sentence summary in English and Spanish structured EXACTLY as:
   - Sentence 1: "[Name] is a [role_title] with [X] years of [Y] experience."
       If Tech specialization is listed: X = years of the FIRST tech in that list, from career_facts. Y = that tech name.
       If no tech specialization: X = most relevant domain years. NEVER use total career years.
   - Sentence 2: Show a CONSISTENT PATTERN of excellence SPECIFIC to a {role_label}.
     Step 1 — identify the 2-3 core capabilities a {role_label} must demonstrate (infer from the role name).
     Step 2 — find the strongest evidence of THOSE capabilities across DIFFERENT time periods.
     Structure: "[Action verb] consistently [role-specific capability]: [result], [result], [result]."
     HARD RULES: No company names. Every result must exist verbatim in data — ZERO fabrication. Use 2-3 real results from DIFFERENT time periods.
   - Sentence 3: {s3_instruction}
   - Sentence 4 (optional): Differentiating capability for this role.
   Rules: Uses ONLY facts from candidate data — zero fabrication. Uses exact numbers from career_facts — never estimate.

Return ONLY this JSON:
{{
  "ats_keywords": ["keyword1", "keyword2", ...],
  "skill_tags": ["tag1", ...],
  "title_en": "<headline in English>",
  "title_es": "<headline in Spanish>",
  "summary_en": "<3-4 sentence summary in English>",
  "summary_es": "<3-4 sentence summary in Spanish>"
}}

--- CANDIDATE DATA (single source of truth — use nothing else) ---
Name: {name}
Target role: {role_title}
{tech_constraint}
Career facts (pre-computed — use these EXACT numbers):
{career_facts}

Full experience history:
{experiences}

Skills: {skills}
"""

_SUMMARIES_PROMPT = """\
You are preparing a one-page CV for a {role_label}. \
Select the {max_entries} most relevant experience entries \
for the target role and write ONE compact paragraph of exactly 2 sentences per entry that:
1. Is strictly grounded in the existing bullets — no fabrication
2. First sentence: most impactful contribution with a strong action verb and measurable result
3. Second sentence: the SPECIFIC {role_label} capability this experience demonstrates. \
   Answer "what does this entry prove about the candidate AS A {role_label}?" \
   Each entry must highlight a different, role-relevant capability angle.
4. Embeds role keywords naturally (no stuffing)
5. Is written in {lang} as flowing prose — no bullets, no line breaks
{tech_constraint_block}
Maximum 45 words total per entry. Rank by relevance to the role.

Return ONLY this JSON:
{{
  "summaries": [
    {{
      "company": "<exact company name>",
      "start_date": "<only the start date, e.g. 2025-04>",
      "ats_score": <0-100>,
      "text": "<2-sentence paragraph>"
    }},
    ...
  ]
}}

--- CANDIDATE EXPERIENCES ---
{experiences}

--- TARGET ROLE ---
Role: {role_title}
Keywords: {keywords}
"""

_PROMPT = """\
⚠ GROUNDING RULE (read before anything else): Every fact in the summary MUST come \
from the candidate data below. Do NOT invent years, achievements, tools, or roles. \
If a detail is not in the data, omit it entirely. Never round or estimate years \
— use the exact numbers from career_facts.

Generate a professional CV profile for a candidate targeting the role of: {role_title}
{tech_constraint}
Write a concise headline (8-12 words) and a 3-4 sentence summary structured EXACTLY as:
  Sentence 1: "[Name] is a [role_title] with [X] years of [Y] experience."
    - If Tech specialization is listed below: X = years of the FIRST tech in that list, from career_facts. Y = that tech name.
    - If no tech specialization: X = most relevant domain years from career_facts. Y = that domain.
    - NEVER use "total professional career" years for X. Always use a tech/domain-specific number.
  Sentence 2: Show a CONSISTENT PATTERN of excellence SPECIFIC to a {role_label}.
    Step 1 — identify the 2-3 core capabilities a {role_label} must demonstrate (infer from the role name).
    Step 2 — find the strongest evidence of THOSE capabilities across DIFFERENT time periods.
    Structure: "[Action verb] consistently [role-specific capability]: [result], [result], [result]."
    HARD RULES:
      - No company names in this sentence — pattern of capability is the subject, not any company.
      - Every result MUST exist verbatim in the candidate data — ZERO fabrication.
      - Use 2-3 real measurable results from DIFFERENT time periods.
  Sentence 3: {s3_instruction}
  Sentence 4 (optional): A differentiating capability — methodologies, leadership, domain knowledge — that adds unique value for this role.

Rules:
- Use ONLY facts present in the candidate data — zero fabrication
- Use the pre-computed career_facts for exact years — do NOT estimate or round differently
- Embed these ATS keywords naturally where real experience supports them: {keywords}
- Write in professional third-person tone
- Generate in BOTH English and Spanish

Return ONLY this JSON:
{{
  "title_en": "<headline in English>",
  "title_es": "<headline in Spanish>",
  "summary_en": "<3-4 sentence summary in English>",
  "summary_es": "<3-4 sentence summary in Spanish>"
}}

--- CANDIDATE DATA (single source of truth — use nothing else) ---
Name: {name}
Target role: {role_title}
{tech_constraint}
Career facts (pre-computed — use these EXACT numbers):
{career_facts}

Full experience history:
{experiences}

Relevant skills: {skills}
"""


def _build_tech_parts(tech_stack: list[str]) -> tuple[str, str]:
    """Returns (tech_constraint block, s3_instruction) for prompt injection."""
    if tech_stack:
        stack_str = ", ".join(tech_stack)
        tech_constraint = f"Tech specialization: {stack_str}\n⚠ Sentence 3 MUST list ONLY these technologies — no others."
        s3_instruction = (
            f"List ONLY the technologies from the Tech specialization ({stack_str}) "
            "that appear in the candidate's actual experience. Do NOT include any technology outside that list."
        )
    else:
        tech_constraint = ""
        s3_instruction = "Name the specific technical stack most relevant to this role from the candidate's experience."
    return tech_constraint, s3_instruction


class ProfileGenerator:
    def __init__(self, ai: AIPort) -> None:
        self._ai = ai

    def create_new_profile(self, cv: CVData, role_title: str, tech_stack: list[str] = [], role_label: str = "") -> dict:
        """Creates a brand-new profile from scratch.

        Infers ATS keywords and skill_tags from market knowledge + cv.yaml.
        Returns dict with: ats_keywords, skill_tags, title_en/es, summary_en/es.
        """
        tech_constraint, s3_instruction = _build_tech_parts(tech_stack)
        prompt = _NEW_PROFILE_PROMPT.format(
            name=f"{cv.name} {cv.lastname}",
            role_title=role_title,
            role_label=role_label or role_title,
            tech_constraint=tech_constraint,
            s3_instruction=s3_instruction,
            career_facts=_compute_career_facts(cv),
            experiences=_format_recent_experience(cv),
            skills=_format_skills(cv),
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        return _parse_json(raw)

    def generate(
        self,
        cv: CVData,
        role_title: str,
        ats_keywords: list[str],
        tech_stack: list[str] = [],
        role_label: str = "",
    ) -> dict[str, str]:
        """Returns dict with title_en, title_es, summary_en, summary_es."""
        tech_constraint, s3_instruction = _build_tech_parts(tech_stack)
        prompt = _PROMPT.format(
            name=f"{cv.name} {cv.lastname}",
            role_title=role_title,
            role_label=role_label or role_title,
            keywords=", ".join(ats_keywords[:15]),
            tech_constraint=tech_constraint,
            s3_instruction=s3_instruction,
            career_facts=_compute_career_facts(cv),
            experiences=_format_recent_experience(cv),
            skills=_format_skills(cv),
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        return _parse_json(raw)

    def generate_profile_summaries(
        self,
        cv: CVData,
        lang: Lang,
        role_title: str,
        ats_keywords: list[str],
        max_entries: int = 8,
        role_label: str = "",
        tech_stack: list[str] = [],
    ) -> list[dict]:
        """Returns [{company, start_date, ats_score, text}, ...] sorted by ats_score desc."""
        tech_constraint, _ = _build_tech_parts(tech_stack)
        tech_constraint_block = (
            f"\nTech focus: when highlighting tools in the second sentence, prefer {', '.join(tech_stack)}."
            if tech_stack else ""
        )
        prompt = _SUMMARIES_PROMPT.format(
            max_entries=max_entries,
            lang=_LANG_LABEL[lang],
            role_label=role_label or role_title,
            experiences=_format_all_experiences(cv, lang),
            role_title=role_title,
            keywords=", ".join(ats_keywords[:15]),
            tech_constraint_block=tech_constraint_block,
        )
        raw = self._ai.complete(prompt, system=_SYSTEM)
        data = _parse_json(raw)
        return sorted(
            data.get("summaries", []),
            key=lambda e: e.get("ats_score", 0),
            reverse=True,
        )


def _compute_career_facts(cv: CVData) -> str:
    """Pre-compute career timeline facts from cv.yaml aptitudes — no hardcoded domains."""
    if not cv.experience:
        return "No experience data available."

    current_year = date.today().year
    lines = []

    # Total career span
    try:
        earliest_year = min(int(e.start_date[:4]) for e in cv.experience)
        lines.append(f"- Total professional career: {current_year - earliest_year} years (since {earliest_year})")
    except (ValueError, AttributeError):
        pass

    # Per-skill first appearance — derived from aptitudes in cv.yaml, nothing hardcoded
    skill_first_year: dict[str, int] = {}
    for exp in cv.experience:
        try:
            year = int(exp.start_date[:4])
        except (ValueError, AttributeError):
            continue
        for aptitude in (exp.aptitudes or []):
            key = aptitude.strip()
            if key and (key not in skill_first_year or year < skill_first_year[key]):
                skill_first_year[key] = year

    if skill_first_year:
        lines.append("- Skill experience (years since first appearance in cv):")
        for skill, first_year in sorted(skill_first_year.items(), key=lambda x: x[1]):
            lines.append(f"    {skill}: {current_year - first_year} years (since {first_year})")

    return "\n".join(lines) if lines else "No computable facts."


def _format_all_experiences(cv: CVData, lang: Lang) -> str:
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
            lines.append(f"Skills: {', '.join(exp.aptitudes)}")
        lines.append("")
    return "\n".join(lines)


def _format_recent_experience(cv: CVData) -> str:
    lines = []
    for i, exp in enumerate(cv.experience):
        lines.append(f"- {exp.role.get(Lang.EN)} at {exp.company} ({exp.start_date}–{exp.end_date})")
        if i < 8:
            for b in exp.bullets[:2]:
                lines.append(f"    {b.get(Lang.EN)}")
    return "\n".join(lines)


def _format_skills(cv: CVData) -> str:
    skills = [s.skill for s in cv.skills]
    return ", ".join(skills[:20])


def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}\n---\n{clean}") from exc
