from collections import defaultdict

import yaml

from domain.models import (
    CVData, Lang, Profile, ThemeConfig,
    CertificationCategory,
    ProjectCategory,
)

TOOLS_LABEL = {
    Lang.ES: "Herramientas/Tecnologías",
    Lang.EN: "Tools/Technologies",
}

# Human-readable labels for skill tag groups
TAG_LABELS = {
    "software_engineer":        "Development",
    "data_engineer":            "Data & Cloud",
    "technical_product_owner":  "Product Management",
    "all":                      "Methodologies",
    "ventas":                   "Sales",
    "atencion_cliente":         "Customer Service",
    "marketing":                "Marketing",
    "emprendimiento":           "Entrepreneurship",
    "administracion":           "Operations",
}

MAX_SKILLS_PER_GROUP = 6


def _norm_date(d: str) -> str:
    """Normalize end_date to rendercv's expected format: 'present' (lowercase)."""
    if d and d.lower() == "present":
        return "present"
    return d


def generate_rendercv_yaml(
    cv: CVData,
    lang: Lang,
    theme_config: ThemeConfig,
    profile: Profile = None,
    summaries: dict[tuple[str, str], str] | None = None,
    ranked_companies: list[tuple[str, str]] | None = None,
) -> str:
    def sort_items(items):
        def key(item):
            d = getattr(item, "end_date", getattr(item, "date", "")).lower()
            return (1 if d == "present" else 0, d)
        return sorted(items, key=key, reverse=True)

    sorted_education = sort_items(cv.education)
    sorted_courses   = sort_items(cv.courses)
    sorted_experience = sort_items(cv.experience)

    career_exp      = [e for e in sorted_experience if not e.is_entrepreneurship]
    entrepreneur_exp = [e for e in sorted_experience if e.is_entrepreneurship]

    pro_certs   = [c for c in cv.certifications if c.category == CertificationCategory.PROFESSIONAL]
    other_certs = [c for c in cv.certifications if c.category == CertificationCategory.EXTRACURRICULAR]

    # Group skills by tag into OneLineEntry objects {label, details}
    filtered_skills = (
        [s for s in cv.skills if any(t in profile.skill_tags for t in s.tags)]
        if profile and profile.skill_tags
        else cv.skills
    )
    groups: dict[str, list[str]] = defaultdict(list)
    for s in filtered_skills:
        tag = s.tags[0] if s.tags else "other"
        groups[tag].append(s.skill)

    skill_list = [
        {
            "label":   TAG_LABELS.get(tag, tag.replace("_", " ").title()),
            "details": ", ".join(skills[:MAX_SKILLS_PER_GROUP]),
        }
        for tag, skills in groups.items()
    ]

    def format_exp(exp, max_bullets: int | None = None):
        end_date = _norm_date(exp.end_date)

        ai_summary = summaries.get((exp.company, exp.start_date)) if summaries else None

        # One-page: only summary, no bullets.
        # Multi-page: summary + bullets.
        if theme_config.one_page:
            bullets = []
        else:
            bullets = [b.get(lang) for b in exp.bullets]
            if exp.description:
                bullets.insert(0, f"_{exp.description.get(lang)}_")
            if exp.aptitudes:
                bullets.append(
                    f"**{TOOLS_LABEL[lang]}:** {', '.join(exp.aptitudes)}"
                )
            if max_bullets is not None:
                bullets = bullets[:max_bullets]

        entry = {
            "company":    exp.company,
            "position":   exp.role.get(lang),
            "location":   exp.location.get(lang),
            "start_date": exp.start_date,
            "end_date":   end_date,
            "highlights": bullets,
        }
        if ai_summary:
            entry["summary"] = ai_summary
        return entry

    # Full pool — theme config decides what appears and in what order.
    # experience and entrepreneurship_experience are built lazily per-section
    # so max_entries / max_bullets from ThemeSection can be applied.
    base_sections = {
        "summary": [profile.summary.get(lang)] if profile else [],
        "ats_keywords": [
            {"label": kw, "details": ""}
            for kw in (profile.ats_keywords if profile else [])
        ],
        "skills": skill_list,
        "education": [
            {
                "institution": edu.institution,
                "area":        edu.degree.get(lang),
                "degree":      "",
                "location":    edu.location.get(lang),
                "start_date":  edu.start_date,
                "end_date":    _norm_date(edu.end_date),
            }
            for edu in sorted_education
        ],
        "courses_and_certifications": [
            {"label": c.issuer, "details": f"{c.name.get(lang)} ({c.date})"}
            for c in sorted_courses
        ],
        "certifications":    [c.name.get(lang) for c in pro_certs],
        "other_achievements": [a.get(lang) for a in (cv.achievements or [])],
        "projects": [
            {"label": p.name.get(lang), "details": p.url or ""}
            if theme_config.one_page else
            {
                "company":    p.name.get(lang),
                "position":   p.category.value.replace("_", " ").title(),
                "location":   p.url or "",
                "start_date": p.start_date,
                "end_date":   _norm_date(p.end_date),
                "highlights": [b.get(lang) for b in p.bullets],
            }
            for p in (cv.projects or [])
        ],
        "languages": [
            {"label": l.name.get(lang), "details": l.level.get(lang)}
            for l in (cv.languages or [])
        ],
    }

    output_sections: dict = {}
    for section in theme_config.sections:
        if section.requires_profile and not profile:
            continue

        if section.key in ("experience", "entrepreneurship_experience"):
            pool = career_exp if section.key == "experience" else entrepreneur_exp
            if ranked_companies:
                order = {key: i for i, key in enumerate(ranked_companies)}
                pool = sorted(
                    [e for e in pool if (e.company, e.start_date) in order],
                    key=lambda e: order[(e.company, e.start_date)],
                )
            if section.max_entries is not None:
                pool = pool[:section.max_entries]
            data = [format_exp(e, section.max_bullets) for e in pool]
        else:
            data = base_sections.get(section.key, [])
            if section.max_entries is not None:
                data = data[:section.max_entries]

        if section.optional and not data:
            continue
        output_sections[section.name] = data

    social_networks = []
    if cv.linkedin:
        social_networks.append({"network": "LinkedIn", "username": cv.linkedin})
    if cv.github:
        social_networks.append({"network": "GitHub", "username": cv.github})

    cv_block: dict = {
        "name":     f"{cv.name} {cv.lastname}",
        "location": cv.location.get(lang),
        "email":    cv.email,
        "phone":    cv.phone,
    }
    if profile and profile.title:
        headline = profile.title.get(lang)
        if headline:
            cv_block["headline"] = headline
    if cv.website:
        cv_block["website"] = cv.website
    if social_networks:
        cv_block["social_networks"] = social_networks
    cv_block["sections"] = output_sections

    return yaml.dump(
        {"cv": cv_block, "design": theme_config.design},
        allow_unicode=True,
        sort_keys=False,
    )
