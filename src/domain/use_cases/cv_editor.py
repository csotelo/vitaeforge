import json
import re

from domain.ports import AIPort

_SYSTEM = (
    "You are an expert CV writer and career coach. "
    "You write ATS-friendly, achievement-focused content in the CAR format "
    "(Challenge → Action → Result). "
    "Respond ONLY with valid JSON — no markdown, no explanation."
)

_EXTRACT_EXPERIENCE_PROMPT = """\
The user will give you a free-form description of a work experience.
Extract all details and write the bullets in CAR format (Challenge → Action → Result).

Return ONLY this JSON:
{{
  "company": "<company name>",
  "location": {{
    "es": "<Ciudad, País>",
    "en": "<City, Country>"
  }},
  "role": {{
    "es": "<job title in Spanish>",
    "en": "<job title in English>"
  }},
  "start_date": "<YYYY-MM or YYYY>",
  "end_date": "<YYYY-MM, YYYY, or Present>",
  "is_entrepreneurship": false,
  "description": {{
    "es": "<one-line context in Spanish, or null>",
    "en": "<one-line context in English, or null>"
  }},
  "aptitudes": ["Tool1", "Tool2"],
  "bullets": [
    {{
      "es": "<CAR bullet in Spanish, starts with action verb>",
      "en": "<CAR bullet in English, starts with action verb>"
    }}
  ]
}}

Rules:
- description: brief company/project context if relevant; null if the company name is self-explanatory
- aptitudes: specific technologies, tools, methodologies — no soft skills
- bullets: 3-6 items, each ≤25 words, strong action verb, measurable result when mentioned
- is_entrepreneurship: true for own business, co-founder, or freelance engagements
- If a field is unknown, use a sensible default ("Present" for open end_date, "" for unknown city)

--- USER INPUT ---
{text}
"""

_UPDATE_EXPERIENCE_PROMPT = """\
Below is an existing CV experience entry (YAML) and the user's instructions for what to change.

Apply the instructions to the existing entry. Keep every field that is NOT mentioned.
Rewrite or add bullets in CAR format (Challenge → Action → Result) as needed.

Return ONLY the complete updated entry as JSON (same structure):
{{
  "company": "...",
  "location": {{"es": "...", "en": "..."}},
  "role": {{"es": "...", "en": "..."}},
  "start_date": "...",
  "end_date": "...",
  "is_entrepreneurship": false,
  "description": {{"es": "...", "en": "..."}} or null,
  "aptitudes": ["..."],
  "bullets": [{{"es": "...", "en": "..."}}]
}}

Rules:
- Preserve existing bullets unless the user explicitly asks to change or remove them
- New bullets must follow CAR format, ≤25 words, strong action verb
- Translate any new content to both Spanish and English

--- CURRENT ENTRY ---
{current_yaml}

--- USER INSTRUCTIONS ---
{text}
"""

_EXTRACT_PROJECT_PROMPT = """\
The user will describe an open source project, community contribution, or activism effort.
Extract structured data and write bullets in CAR format.

Return ONLY this JSON:
{{
  "name": {{
    "es": "<project name in Spanish>",
    "en": "<project name in English>"
  }},
  "url": "<URL or null>",
  "category": "<open_source | activism | community>",
  "start_date": "<YYYY-MM or YYYY>",
  "end_date": "<YYYY-MM, YYYY, or Present>",
  "bullets": [
    {{
      "es": "<CAR bullet in Spanish>",
      "en": "<CAR bullet in English>"
    }}
  ]
}}

Rules:
- open_source: code contribution, personal project published publicly
- activism: advocacy, campaign, social cause
- community: meetups, mentoring, user groups, internal guilds
- bullets: 1-4 items in CAR format, starting with action verb

--- USER INPUT ---
{text}
"""

_UPDATE_PROJECT_PROMPT = """\
Below is an existing CV project entry (YAML) and the user's instructions for what to change.

Apply the instructions. Keep every field that is NOT mentioned.
Rewrite or add bullets in CAR format as needed.

Return ONLY the complete updated entry as JSON:
{{
  "name": {{"es": "...", "en": "..."}},
  "url": "..." or null,
  "category": "<open_source | activism | community>",
  "start_date": "...",
  "end_date": "...",
  "bullets": [{{"es": "...", "en": "..."}}]
}}

--- CURRENT ENTRY ---
{current_yaml}

--- USER INSTRUCTIONS ---
{text}
"""

_CLASSIFY_SKILLS_PROMPT = """\
The user will give you a list of skills, tools, and technologies.
Classify each one with relevant tags from this fixed set:
  software_engineer, data_engineer, technical_product_owner, all

Return ONLY this JSON:
{{
  "skills": [
    {{
      "skill": "<exact skill name, normalized>",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Rules:
- Use "all" for cross-cutting skills (Agile, leadership, communication, Git, etc.)
- A skill can have multiple domain tags
- Normalize: "python" → "Python", "aws" → "AWS", "postgresql" → "PostgreSQL"
- De-duplicate: one entry per skill even if the user listed it twice
- Ignore blank entries

--- USER INPUT ---
{text}
"""

_REVIEW_BULLETS_PROMPT = """\
Review the following CV bullets and rewrite each one in strict CAR format:
  Challenge → Action → Result
Rules:
- Start with a strong past-tense action verb
- Include a measurable result (infer reasonable numbers from context if needed)
- Keep each bullet ≤25 words
- Write the improved version in BOTH English and Spanish

Return ONLY this JSON:
{{
  "reviewed": [
    {{
      "original_en": "<original English bullet>",
      "improved_en": "<improved CAR bullet in English>",
      "original_es": "<original Spanish bullet>",
      "improved_es": "<improved CAR bullet in Spanish>"
    }}
  ]
}}

--- EXPERIENCE ---
Company : {company}
Role    : {role}
Period  : {start_date} – {end_date}

Bullets:
{bullets}
"""


class CVEditor:
    def __init__(self, ai: AIPort) -> None:
        self._ai = ai

    def extract_experience(self, text: str, current_entry: dict | None = None) -> dict:
        """Parse free-form experience description → structured dict with CAR bullets.

        If current_entry is provided, applies the text as update instructions on top
        of the existing entry rather than extracting from scratch.
        """
        if current_entry:
            import yaml as _yaml
            current_yaml = _yaml.dump(current_entry, allow_unicode=True, sort_keys=False)
            prompt = _UPDATE_EXPERIENCE_PROMPT.format(current_yaml=current_yaml, text=text)
        else:
            prompt = _EXTRACT_EXPERIENCE_PROMPT.format(text=text)
        return _parse_json(self._ai.complete(prompt, system=_SYSTEM))

    def extract_project(self, text: str, current_entry: dict | None = None) -> dict:
        """Parse free-form project description → structured dict with CAR bullets.

        If current_entry is provided, applies the text as update instructions.
        """
        if current_entry:
            import yaml as _yaml
            current_yaml = _yaml.dump(current_entry, allow_unicode=True, sort_keys=False)
            prompt = _UPDATE_PROJECT_PROMPT.format(current_yaml=current_yaml, text=text)
        else:
            prompt = _EXTRACT_PROJECT_PROMPT.format(text=text)
        return _parse_json(self._ai.complete(prompt, system=_SYSTEM))

    def classify_skills(self, text: str) -> list[dict]:
        """Classify comma-separated or line-separated skills → [{skill, tags}]."""
        prompt = _CLASSIFY_SKILLS_PROMPT.format(text=text)
        data = _parse_json(self._ai.complete(prompt, system=_SYSTEM))
        return data.get("skills", [])

    def review_bullets(self, company: str, role: str, start_date: str, end_date: str,
                       bullets: list[dict]) -> list[dict]:
        """Review bullets for a single experience → [{original_en/es, improved_en/es}]."""
        formatted = "\n".join(
            f"  EN: {b.get('en', '')}\n  ES: {b.get('es', '')}"
            for b in bullets
        )
        prompt = _REVIEW_BULLETS_PROMPT.format(
            company=company, role=role,
            start_date=start_date, end_date=end_date,
            bullets=formatted,
        )
        data = _parse_json(self._ai.complete(prompt, system=_SYSTEM))
        return data.get("reviewed", [])


def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}\n---\n{clean}") from exc
