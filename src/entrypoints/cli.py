"""
VitaeForge — Job search assistant.

Usage:
  # Auto-detects the person if only one cv.yaml exists under people/
  vitaeforge --role data_engineer --lang en
  vitaeforge --role data_engineer --lang en --refresh         # force profile update
  vitaeforge --role data_engineer --lang en --theme harmony   # one-page variant

  # Multiple people: specify with --person
  vitaeforge --person carlos_sotelo --role data_engineer --lang en

  # Update the theme stored in the profile (non-one-page themes only)
  vitaeforge --role data_engineer --lang en --theme moderncv --overwritetheme

  # CV optimized for a specific job posting (file path or URL)
  vitaeforge --jd jobs/job.txt --lang en
  vitaeforge --jd https://linkedin.com/jobs/123 --lang en --theme harmony
"""

import argparse
import hashlib
import os
import re
import sys
import urllib.request

import yaml
from dotenv import load_dotenv
load_dotenv()

from application.cv_generator import generate_rendercv_yaml
from domain.models import CVData, Lang, LocalizedString, Profile
from domain.use_cases import JDAnalyzer, ATSScorer, ExperienceEnricher, ProfileGenerator, CVEditor
from infrastructure.ai import build_ai_adapter, DEFAULT_MODEL, REGISTRY
from infrastructure.persistence import (
    load_cv_data, load_theme_config,
    upsert_experience, upsert_project, upsert_education,
    upsert_skills, upsert_language, upsert_certification,
    append_course, append_achievement,
)
from infrastructure.renderer import RendercvRunner

GENERATED_ROOT = "generated"


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vitaeforge",
        description="CV generation assistant. Generic by role or optimized for a job posting.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--role",          help="Target role profile name (e.g. data_engineer)")
    mode.add_argument("--jd",            help="Job description: file path or URL")
    mode.add_argument("--create-person", metavar="NAME",
                      help="Scaffold a new person directory under people/ (e.g. jane_doe)")
    mode.add_argument("--edit",           action="store_true",
                      help="Interactive editor: add or update CV content with AI-assisted CAR bullets")
    parser.add_argument("--person",  default=None, help="Person folder name under people/ (auto-detected if only one exists)")
    parser.add_argument("--lang",    required=False, default=None, choices=["en", "es"])
    parser.add_argument("--theme",   default=None, help="Theme override (default: from profile > VITAEFORGE_THEME > moderncv)")
    parser.add_argument("--model",   default=DEFAULT_MODEL,
                        help=f"AI model (default: {DEFAULT_MODEL}). Available: {', '.join(sorted(REGISTRY))}")
    parser.add_argument("--refresh",       action="store_true", help="Force profile regeneration (--role mode)")
    parser.add_argument("--auto",          action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--overwritetheme", action="store_true",
                        help="Update theme stored in profile.yaml (--role mode, non-one-page themes only)")
    return parser.parse_args()


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _find_cv_path(person: str | None, people_dir: str = "people") -> str:
    if not os.path.isdir(people_dir):
        sys.exit(f"Error: '{people_dir}/' directory not found.")

    candidates = sorted(
        d for d in os.listdir(people_dir)
        if os.path.isfile(os.path.join(people_dir, d, "cv.yaml"))
    )

    if not candidates:
        sys.exit(
            f"Error: no cv.yaml found in {people_dir}/.\n"
            f"  Create one at: {people_dir}/<name>/cv.yaml"
        )

    if person:
        if person not in candidates:
            options = "\n".join(f"  --person {c}" for c in candidates)
            sys.exit(f"Error: '{person}' not found in {people_dir}/. Available:\n{options}")
        return os.path.join(people_dir, person, "cv.yaml")

    if len(candidates) == 1:
        return os.path.join(people_dir, candidates[0], "cv.yaml")

    options = "\n".join(f"  --person {c}" for c in candidates)
    sys.exit(f"Error: multiple people found in {people_dir}/. Use --person to specify one:\n{options}")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]

_TECH_ALIASES = {
    "fastapi": "FastAPI", "aws": "AWS", "sql": "SQL", "api": "API",
    "cqrs": "CQRS", "drf": "Django REST Framework", "dbt": "dbt",
    "etl": "ETL", "crm": "CRM", "erp": "ERP", "llm": "LLM",
    "ai": "AI", "ml": "ML", "gcp": "GCP", "ci": "CI/CD",
}

def _parse_role_name(role: str) -> tuple[str, list[str]]:
    """'software_engineer__python_django_fastapi_aws' → ('Software Engineer', ['Python', 'Django', 'FastAPI', 'AWS'])."""
    if "__" in role:
        role_part, tech_part = role.split("__", 1)
        role_label = role_part.replace("_", " ").title()
        tech_stack = [_TECH_ALIASES.get(t.lower(), t.title()) for t in tech_part.split("_")]
    else:
        role_label = role.replace("_", " ").title()
        tech_stack = []
    return role_label, tech_stack

def _person_slug(cv: CVData) -> str:
    return f"{cv.name}_{cv.lastname}".lower().replace(" ", "_")

def _output_dirs(person: str) -> tuple[str, str]:
    base = os.path.join(GENERATED_ROOT, person)
    return os.path.join(base, "yaml"), os.path.join(base, "pdf")

def _cv_hash(cv_path: str) -> str:
    with open(cv_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

def _load_jd_text(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        print("  Fetching JD from URL...", end=" ", flush=True)
        with urllib.request.urlopen(source, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        print("done.")
        return text
    if os.path.isfile(source):
        with open(source, encoding="utf-8") as f:
            return f.read().strip()
    sys.exit(f"Error: JD not found: {source}")

def _section(title: str) -> None:
    print(f"\n{'─' * 60}\n  {title}\n{'─' * 60}")

def _confirm(message: str) -> bool:
    return input(f"\n  {message} [Y/n]: ").strip().lower() in ("", "y", "yes")

def _resolve_theme(cli_theme: str | None, profile_theme: str | None = None) -> str:
    """Priority: --theme CLI > VITAEFORGE_THEME env > profile.yaml theme > moderncv."""
    return (
        cli_theme
        or os.environ.get("VITAEFORGE_THEME")
        or profile_theme
        or "moderncv"
    )

def _render(yaml_path: str, pdf_path: str, theme_name: str) -> None:
    theme_dir = f"themes/{theme_name}" if os.path.isdir(f"themes/{theme_name}") else None
    RendercvRunner().render(yaml_path, pdf_path, theme_dir=theme_dir)

def _experience_key(h: dict) -> tuple[str, str]:
    """Normalizes start_date from the AI (may include full period) to match cv.yaml start_date."""
    raw = h.get("start_date", "")
    start = raw.split("–")[0].strip() if "–" in raw else raw.strip()
    return (h["company"], start)

def _write_yaml(yaml_str: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(yaml_str)


# ── CREATE PERSON MODE ─────────────────────────────────────────────────────────

_CV_SCAFFOLD = """\
# VitaeForge — CV data file
# Fill in your real data. All text fields support bilingual content (es/en).
# Run: vitaeforge --role <role> --lang en   to generate your first CV.

name: Jane                          # First name(s)
lastname: Doe                       # Last name(s)
email: jane.doe@example.com
phone: "+1 555 000 0000"
website: https://dev.to/janedoe     # Optional — remove if not applicable
linkedin: janedoe                   # Username only, not the full URL
github: janedoe                     # Optional — remove if not applicable
location:
  es: Ciudad, País
  en: City, Country

experience:
  - company: Acme Corp
    location:
      es: Ciudad, País
      en: City, Country
    role:
      es: Título del puesto en español
      en: Job Title in English
    start_date: "2023-01"           # YYYY-MM format
    end_date: "Present"             # or "2024-12"
    is_entrepreneurship: false      # true → shown in Entrepreneurship section
    description:                    # Optional — one line of context, shown in italics
      es: Descripción breve del contexto del rol.
      en: Brief context description for this role.
    aptitudes: [Python, Docker, AWS]  # Tools / technologies used in this role
    bullets:
      # CAR format: Challenge → Action → Result. Start with an action verb.
      - es: "Logro con verbo de acción, impacto medible y contexto."
        en: "Achievement with action verb, measurable impact, and context."

skills:
  # Tags control which skills appear for each profile type.
  # Available tags: software_engineer, data_engineer, technical_product_owner, all
  - skill: Python
    tags: [software_engineer, data_engineer]
  - skill: SQL
    tags: [software_engineer, data_engineer]

education:
  - institution: Example University
    location:
      es: Ciudad, País
      en: City, Country
    degree:
      es: Ingeniería de Sistemas
      en: Systems Engineering
    start_date: "2015"
    end_date: "2019"

courses:
  # A course is training attended — no credential ID issued.
  - name:
      es: Nombre del curso
      en: Course Name
    issuer: Issuer Name
    date: "2023-06"                 # YYYY-MM format

certifications:
  # A certification requires a credential_id — if you don't have one, it's a course.
  - name:
      es: Nombre de certificación
      en: Certification Name
    issuer: Certifying Body
    date: "2023-06"                 # YYYY-MM — date earned
    credential_id: "ABC123"         # required — issued by the certifying body
    credential_url: "https://..."   # optional — online verification link
    category: professional          # professional or extracurricular

achievements:
  # Non-credentialed recognitions, community roles, or extracurricular activities.
  - es: "Rol o reconocimiento en español."
    en: "Role or recognition in English."

projects:
  # Open source contributions, community activism, or personal projects.
  - name:
      es: Nombre del proyecto
      en: Project Name
    url: https://github.com/you/project   # optional
    category: open_source                 # open_source, activism, or community
    start_date: "2024-01"
    end_date: "Present"
    bullets:
      - es: "Logro o contribución en español (formato CAR)."
        en: "Achievement or contribution in English (CAR format)."

languages:
  - name:
      es: Inglés
      en: English
    level:
      es: Avanzado - B2
      en: Advanced - B2
"""


def _run_create_person(name: str, people_dir: str = "people") -> None:
    target = os.path.join(people_dir, name)
    if os.path.exists(target):
        sys.exit(f"Error: '{target}/' already exists.")

    cv_path      = os.path.join(target, "cv.yaml")
    profiles_dir = os.path.join(target, "profiles")

    os.makedirs(profiles_dir, exist_ok=True)
    with open(cv_path, "w", encoding="utf-8") as f:
        f.write(_CV_SCAFFOLD)

    print(f"\n  Created: {cv_path}")
    print(f"  Created: {profiles_dir}/")
    print(f"\n  Next steps:")
    print(f"    1. Edit {cv_path} with your real data")
    print(f"    2. vitaeforge --person {name} --role <role> --lang en")
    print()


# ── EDIT MODE ─────────────────────────────────────────────────────────────────

def _read_brain_dump(prompt: str) -> str:
    """Read multi-line input from user. Empty line terminates."""
    print(f"\n  {prompt}")
    print("  (Press Enter on an empty line when done)\n")
    lines = []
    while True:
        line = input()
        if not line and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _ask(prompt: str, default: str = "") -> str:
    value = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
    return value or default


def _ask_localized(label: str) -> dict:
    return {
        "es": _ask(f"{label} (es)"),
        "en": _ask(f"{label} (en)"),
    }


def _preview(data: dict) -> None:
    print("\n" + "─" * 60)
    print(yaml.dump(data, allow_unicode=True, sort_keys=False).rstrip())
    print("─" * 60)


# ── Edit: Experience ───────────────────────────────────────────────────────────

def _pick_experience(cv_path: str) -> dict | None:
    """Show numbered list of experiences; return selected entry or None."""
    with open(cv_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    experiences = raw.get("experience", [])
    if not experiences:
        print("  No experiences in cv.yaml yet.")
        return None
    print()
    for i, exp in enumerate(experiences):
        role_en = (exp.get("role") or {}).get("en", "?")
        print(f"  {i + 1}. {exp.get('company')} — {role_en} ({exp.get('start_date')})")
    print()
    choice = _ask("Enter number").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(experiences)):
        print("  Invalid choice.")
        return None
    return experiences[int(choice) - 1]


def _parse_selection(raw: str, total: int) -> list[int]:
    """Parse '1,3' or 'all' into zero-based index list."""
    if raw.strip().lower() == "all":
        return list(range(total))
    try:
        indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip()]
        return [i for i in indices if 0 <= i < total]
    except ValueError:
        return []


def _edit_bullets_interactive(editor: CVEditor, exp: dict) -> list[dict]:
    """Per-bullet editing flow. Returns the updated bullets list."""
    bullets = list(exp.get("bullets") or [])

    if not bullets:
        print("  No bullets yet for this experience.")
    else:
        print()
        for i, b in enumerate(bullets):
            print(f"  {i + 1}. {b.get('en') or b.get('es', '?')}")
        print()

        raw = _ask(
            "Select bullets to modify (e.g. 1,3 | all | Enter to skip)"
        ).strip()

        if raw:
            selected = _parse_selection(raw, len(bullets))
            if not selected:
                print("  Invalid selection — skipping bullet editing.")
            else:
                for idx in selected:
                    b = bullets[idx]
                    print(f"\n  Bullet {idx + 1}: \"{b.get('en') or b.get('es', '?')}\"")
                    action = _ask(
                        "[k]eep  [e]dit manually  [a]I improve  [d]elete", "k"
                    ).strip().lower()

                    if action in ("e", "edit"):
                        new_en = input(f"  EN [{b.get('en', '')}]: ").strip()
                        new_es = input(f"  ES [{b.get('es', '')}]: ").strip()
                        bullets[idx] = {
                            "en": new_en or b.get("en", ""),
                            "es": new_es or b.get("es", ""),
                        }

                    elif action in ("a", "ai"):
                        print("  Improving with AI...", end=" ", flush=True)
                        try:
                            reviewed = editor.review_bullets(
                                company=exp.get("company", ""),
                                role=(exp.get("role") or {}).get("en", ""),
                                start_date=exp.get("start_date", ""),
                                end_date=exp.get("end_date", ""),
                                bullets=[b],
                            )
                        except ValueError as exc:
                            print(f"\n  AI error: {exc}")
                            continue
                        print("done.")
                        if reviewed:
                            item = reviewed[0]
                            print(f"\n  Original : {item.get('original_en')}")
                            print(f"  Improved : {item.get('improved_en')}")
                            keep = _ask("Use improved version?", "Y/n").strip().lower()
                            if keep in ("", "y", "yes"):
                                bullets[idx] = {
                                    "en": item.get("improved_en", b.get("en", "")),
                                    "es": item.get("improved_es", b.get("es", "")),
                                }

                    elif action in ("d", "delete"):
                        bullets[idx] = None

                bullets = [b for b in bullets if b is not None]

    # Offer to add new bullets
    print()
    add = _ask("Add new bullet(s)? [y/N]", "N").strip().lower()
    if add in ("y", "yes"):
        text = _read_brain_dump(
            "Describe the new achievement(s) — any format, CAR hints welcome.\n"
            "  (Challenge → Action → Result)"
        )
        if text:
            print("  Extracting with AI...", end=" ", flush=True)
            try:
                extracted = editor.extract_experience(text)
                new_bullets = extracted.get("bullets", [])
                bullets.extend(new_bullets)
                print(f"done. ({len(new_bullets)} new bullet(s) added)")
            except ValueError as exc:
                print(f"\n  AI error: {exc}")

    return bullets


def _edit_experience(editor: CVEditor, cv_path: str) -> None:
    mode = _ask("Add new or update existing?", "N/u").strip().lower()

    if mode in ("u", "update"):
        exp = _pick_experience(cv_path)
        if exp is None:
            return

        role_en = (exp.get("role") or {}).get("en", "?")
        print(f"\n  {exp.get('company')} — {role_en}  ({exp.get('start_date')} – {exp.get('end_date')})")

        # Step 1: per-bullet editing
        updated_bullets = _edit_bullets_interactive(editor, exp)

        # Step 2: metadata changes (optional brain dump)
        print()
        text = _read_brain_dump(
            "Any other changes? (role title, dates, aptitudes, description)\n"
            "  Leave empty to skip."
        )

        if text:
            merged = {**exp, "bullets": updated_bullets}
            print("\n  Processing with AI...", end=" ", flush=True)
            try:
                result = editor.extract_experience(text, current_entry=merged)
            except ValueError as exc:
                print(f"\n  AI error: {exc}")
                result = merged
            print("done.")
        else:
            result = {**exp, "bullets": updated_bullets}

    else:
        text = _read_brain_dump(
            "Describe the experience (any language, any format).\n"
            "  Include: company, role, dates, location, achievements, tools used."
        )
        if not text:
            print("  Aborted.")
            return
        print("\n  Extracting with AI...", end=" ", flush=True)
        try:
            result = editor.extract_experience(text)
        except ValueError as exc:
            print(f"\n  AI error: {exc}")
            return
        print("done.")

    _preview(result)
    if not _confirm("Save to cv.yaml?"):
        print("  Discarded.")
        return

    replaced = upsert_experience(cv_path, result)
    print(f"  {'Updated' if replaced else 'Added'}: {result.get('company')} ({result.get('start_date')}).")


# ── Edit: Project ──────────────────────────────────────────────────────────────

def _pick_project(cv_path: str) -> dict | None:
    """Show numbered list of projects; return selected entry or None."""
    with open(cv_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    projects = raw.get("projects", [])
    if not projects:
        print("  No projects in cv.yaml yet.")
        return None
    print()
    for i, p in enumerate(projects):
        name_en = (p.get("name") or {}).get("en", "?")
        print(f"  {i + 1}. {name_en} ({p.get('category')}, {p.get('start_date')})")
    print()
    choice = _ask("Enter number").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(projects)):
        print("  Invalid choice.")
        return None
    return projects[int(choice) - 1]


def _edit_project(editor: CVEditor, cv_path: str) -> None:
    mode = _ask("Add new or update existing?", "N/u").strip().lower()
    current_entry = None

    if mode in ("u", "update"):
        current_entry = _pick_project(cv_path)
        if current_entry is None:
            return
        print("\n  Current entry:")
        _preview(current_entry)
        text = _read_brain_dump(
            "Describe what to change or add.\n"
            "  Only mention what changes — everything else is kept as-is."
        )
    else:
        text = _read_brain_dump(
            "Describe the project (any format).\n"
            "  Include: name, URL, category (open_source/activism/community), dates, what you did."
        )

    if not text:
        print("  Aborted.")
        return

    print("\n  Processing with AI...", end=" ", flush=True)
    try:
        result = editor.extract_project(text, current_entry=current_entry)
    except ValueError as exc:
        print(f"\n  AI error: {exc}")
        return
    print("done.")

    _preview(result)
    if not _confirm("Save to cv.yaml?"):
        print("  Discarded.")
        return

    replaced = upsert_project(cv_path, result)
    name_en = (result.get("name") or {}).get("en", "?")
    print(f"  {'Updated' if replaced else 'Added'}: {name_en}.")


# ── Edit: Skills ───────────────────────────────────────────────────────────────

def _edit_skills(editor: CVEditor, cv_path: str) -> None:
    text = _read_brain_dump(
        "List your skills, tools, and technologies.\n"
        "  You can use commas, lines, or any free-form format."
    )
    if not text:
        print("  Aborted.")
        return

    print("\n  Classifying with AI...", end=" ", flush=True)
    try:
        skills = editor.classify_skills(text)
    except ValueError as exc:
        print(f"\n  AI error: {exc}")
        return
    print("done.")

    _preview({"skills": skills})
    if not _confirm("Merge into cv.yaml?"):
        print("  Discarded.")
        return

    added, updated = upsert_skills(cv_path, skills)
    print(f"  Skills: {added} added, {updated} updated.")


# ── Edit: Education ─────────────────────────────────────────────────────────────

def _edit_education(cv_path: str) -> None:
    print("\n  --- Education ---")
    entry = {
        "institution": _ask("Institution name"),
        "location":    _ask_localized("Location"),
        "degree":      _ask_localized("Degree / program"),
        "start_date":  _ask("Start date (YYYY or YYYY-MM)"),
        "end_date":    _ask("End date (YYYY, YYYY-MM, or Present)", "Present"),
    }
    _preview(entry)
    if not _confirm("Save to cv.yaml?"):
        print("  Discarded.")
        return
    replaced = upsert_education(cv_path, entry)
    print(f"  {'Updated' if replaced else 'Added'}: {entry['institution']}.")


# ── Edit: Language ──────────────────────────────────────────────────────────────

def _edit_language(cv_path: str) -> None:
    print("\n  --- Language ---")
    entry = {
        "name":  _ask_localized("Language name"),
        "level": _ask_localized("Proficiency level (e.g. Advanced - B2 / Avanzado - B2)"),
    }
    _preview(entry)
    if not _confirm("Save to cv.yaml?"):
        print("  Discarded.")
        return
    replaced = upsert_language(cv_path, entry)
    name_en = entry["name"].get("en", "?")
    print(f"  {'Updated' if replaced else 'Added'}: {name_en}.")


# ── Edit: Course ────────────────────────────────────────────────────────────────

def _edit_course(cv_path: str) -> None:
    print("\n  --- Course (no credential ID — if you have one, use Certification) ---")
    entry = {
        "name":   _ask_localized("Course name"),
        "issuer": _ask("Issuing organization"),
        "date":   _ask("Date earned (YYYY-MM)"),
    }
    _preview(entry)
    if not _confirm("Append to cv.yaml?"):
        print("  Discarded.")
        return
    append_course(cv_path, entry)
    name_en = entry["name"].get("en", "?")
    print(f"  Added course: {name_en}.")


# ── Edit: Certification ─────────────────────────────────────────────────────────

def _edit_certification(cv_path: str) -> None:
    print("\n  --- Certification (requires a credential ID) ---")
    entry = {
        "name":           _ask_localized("Certification name"),
        "issuer":         _ask("Issuing body"),
        "date":           _ask("Date earned (YYYY-MM)"),
        "credential_id":  _ask("Credential ID"),
        "credential_url": _ask("Credential URL (optional)") or None,
        "category":       _ask("Category", "professional"),
    }
    if not entry["credential_id"]:
        print("  credential_id is required for certifications. Use Course instead.")
        return
    _preview(entry)
    if not _confirm("Save to cv.yaml?"):
        print("  Discarded.")
        return
    replaced = upsert_certification(cv_path, entry)
    name_en = entry["name"].get("en", "?")
    print(f"  {'Updated' if replaced else 'Added'}: {name_en}.")


# ── Edit: Achievement ───────────────────────────────────────────────────────────

def _edit_achievement(cv_path: str) -> None:
    print("\n  --- Achievement / Recognition / Community Role ---")
    entry = _ask_localized("Achievement")
    if not entry.get("en") and not entry.get("es"):
        print("  Aborted.")
        return
    _preview(entry)
    if not _confirm("Append to cv.yaml?"):
        print("  Discarded.")
        return
    append_achievement(cv_path, entry)
    print(f"  Added: {entry.get('en') or entry.get('es')}.")


# ── Edit: Review bullets ────────────────────────────────────────────────────────

def _review_bullets(editor: CVEditor, cv_path: str) -> None:
    import yaml as _yaml
    with open(cv_path, "r", encoding="utf-8") as f:
        raw = _yaml.safe_load(f)
    experiences = raw.get("experience", [])
    if not experiences:
        print("  No experiences found in cv.yaml.")
        return

    print("\n  Select an experience to review:\n")
    for i, exp in enumerate(experiences):
        print(f"  {i + 1}. {exp.get('company')} — {(exp.get('role') or {}).get('en', '?')} ({exp.get('start_date')})")
    print()

    raw_choice = _ask("Enter number").strip()
    if not raw_choice.isdigit() or not (1 <= int(raw_choice) <= len(experiences)):
        print("  Invalid choice.")
        return

    exp = experiences[int(raw_choice) - 1]
    bullets = exp.get("bullets", [])
    if not bullets:
        print("  This experience has no bullets to review.")
        return

    print(f"\n  Reviewing {len(bullets)} bullet(s) with AI...", end=" ", flush=True)
    try:
        reviewed = editor.review_bullets(
            company=exp.get("company", ""),
            role=(exp.get("role") or {}).get("en", ""),
            start_date=exp.get("start_date", ""),
            end_date=exp.get("end_date", ""),
            bullets=bullets,
        )
    except ValueError as exc:
        print(f"\n  AI error: {exc}")
        return
    print("done.\n")

    kept_bullets = []
    for item in reviewed:
        print(f"  Original : {item.get('original_en')}")
        print(f"  Improved : {item.get('improved_en')}")
        choice = _ask("Use improved version?", "Y/n").strip().lower()
        if choice in ("", "y", "yes"):
            kept_bullets.append({
                "es": item.get("improved_es", item.get("original_es", "")),
                "en": item.get("improved_en", item.get("original_en", "")),
            })
        else:
            kept_bullets.append({
                "es": item.get("original_es", ""),
                "en": item.get("original_en", ""),
            })
        print()

    exp["bullets"] = kept_bullets
    upsert_experience(cv_path, exp)
    print(f"  Bullets updated for {exp.get('company')}.")


# ── Edit: Main menu ─────────────────────────────────────────────────────────────

def _run_edit_mode(args, cv_path: str, ai) -> None:
    editor = CVEditor(ai)
    while True:
        _section("VitaeForge CV Editor")
        print(f"  CV: {cv_path}\n")
        print("  What would you like to add or update?\n")
        print("  1. Experience         (brain dump → AI extracts + CAR bullets)")
        print("  2. Project            (brain dump → AI extracts + CAR bullets)")
        print("  3. Skills             (brain dump → AI classifies)")
        print("  4. Education          (guided wizard)")
        print("  5. Language           (guided wizard)")
        print("  6. Course             (guided wizard)")
        print("  7. Certification      (guided wizard)")
        print("  8. Achievement        (one-liner)")
        print("  9. Review bullets     (pick experience → AI suggests improvements)")
        print("  0. Exit")

        choice = input("\n  → ").strip()

        if choice == "0":
            print("\n  Done.\n")
            break
        elif choice == "1":
            _edit_experience(editor, cv_path)
        elif choice == "2":
            _edit_project(editor, cv_path)
        elif choice == "3":
            _edit_skills(editor, cv_path)
        elif choice == "4":
            _edit_education(cv_path)
        elif choice == "5":
            _edit_language(cv_path)
        elif choice == "6":
            _edit_course(cv_path)
        elif choice == "7":
            _edit_certification(cv_path)
        elif choice == "8":
            _edit_achievement(cv_path)
        elif choice == "9":
            _review_bullets(editor, cv_path)
        else:
            print("  Invalid choice — enter a number from 0 to 9.")


# ── ROLE MODE ──────────────────────────────────────────────────────────────────

def _run_role_mode(args, cv: CVData, lang: Lang, ai, cv_path: str) -> None:
    cv_dir = os.path.dirname(os.path.abspath(cv_path))
    profile_path = os.path.join(cv_dir, "profiles", f"{args.role}.yaml")

    role_label, tech_stack = _parse_role_name(args.role)

    # Resolve the requested theme early so we know if it's one-page before loading the profile
    _early_theme_config = load_theme_config(_resolve_theme(args.theme))

    if not os.path.isfile(profile_path):
        print(f"\n  Profile '{args.role}' not found — creating with AI...", end=" ", flush=True)
        result = ProfileGenerator(ai).create_new_profile(cv, role_label, tech_stack, role_label=role_label)

        # Theme for the profile: always from env (never one-page)
        default_theme = os.environ.get("VITAEFORGE_THEME") or "moderncv"
        if load_theme_config(default_theme).one_page:
            default_theme = "moderncv"

        raw = {
            "name":         args.role,
            "title":        {"en": result["title_en"],   "es": result["title_es"]},
            "summary":      {"en": result["summary_en"], "es": result["summary_es"]},
            "ats_keywords": result.get("ats_keywords", []),
            "skill_tags":   result.get("skill_tags", []),
            "theme":        default_theme,
            "_meta":        {"cv_hash": _cv_hash(cv_path)},
        }
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, sort_keys=False)
        print("done.")
    else:
        with open(profile_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

    current_hash = _cv_hash(cv_path)
    stored_hash  = (raw.get("_meta") or {}).get("cv_hash")
    needs_refresh = args.refresh or stored_hash != current_hash

    generator = ProfileGenerator(ai)
    save_needed = False

    if needs_refresh:
        reason = "forced" if args.refresh else "cv.yaml changed"
        print(f"\n  Refreshing profile ({reason})...", end=" ", flush=True)
        role_title   = (raw.get("title") or {}).get("en") or role_label
        ats_keywords = raw.get("ats_keywords") or []
        result = generator.generate(cv, role_title, ats_keywords, tech_stack, role_label=role_label)
        raw["title"]   = {"es": result["title_es"],   "en": result["title_en"]}
        raw["summary"] = {"es": result["summary_es"], "en": result["summary_en"]}
        raw.setdefault("_meta", {})["cv_hash"] = current_hash
        raw.pop("profile_summaries", None)  # invalidate all cached summaries
        save_needed = True
        print("done.")
    else:
        print(f"\n  Profile up to date.")

    profile_data = {k: v for k, v in raw.items() if k != "_meta"}
    profile      = Profile(**profile_data)
    profile_theme = getattr(profile, "theme", None)
    theme_name    = _resolve_theme(args.theme, profile_theme)
    theme_config  = load_theme_config(theme_name)

    # Ensure summaries exist for this language — generated at profile time, used by all themes
    cached = (raw.get("profile_summaries") or {}).get(lang.value)
    # Invalidate if cached format is outdated (missing start_date field)
    if cached and any("start_date" not in s for s in cached):
        cached = None
    if not cached:
        profile_title = profile.title.get(lang) if profile.title else args.role.replace("_", " ").title()
        print(f"\n  Generating summaries ({lang.value})...", end=" ", flush=True)
        cached = generator.generate_profile_summaries(
            cv, lang, profile_title, profile.ats_keywords or [], len(cv.experience),
            role_label=role_label, tech_stack=tech_stack,
        )
        raw.setdefault("profile_summaries", {})[lang.value] = cached
        save_needed = True
        print(f"done. ({len(cached)} entries)")
    else:
        print(f"\n  Summaries loaded from profile ({lang.value}, {len(cached)} entries).")

    if save_needed:
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, sort_keys=False)

    # All themes use per-role summaries; one-page also ranks and limits by ats_score
    summaries        = {_experience_key(s): s["text"] for s in cached}
    ranked_companies = None

    if theme_config.one_page:
        max_e = next((s.max_entries for s in theme_config.sections if s.key == "experience"), 8)
        top              = cached[:max_e]
        ranked_companies = [_experience_key(s) for s in top]
        summaries        = {_experience_key(s): s["text"] for s in top}
    elif args.overwritetheme and args.theme:
        raw["theme"] = theme_name
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, sort_keys=False)
        print(f"\n  Profile theme updated to '{theme_name}'.")

    yaml_str = generate_rendercv_yaml(cv, lang, theme_config, profile, summaries, ranked_companies)

    person        = _person_slug(cv)
    yaml_dir, pdf_dir = _output_dirs(person)
    os.makedirs(yaml_dir, exist_ok=True)
    os.makedirs(pdf_dir,  exist_ok=True)

    suffix    = "_one_page" if theme_config.one_page else ""
    base      = f"{person}_{args.role}_{lang.value}{suffix}"
    yaml_path = os.path.join(yaml_dir, f"{base}.yaml")
    pdf_path  = os.path.join(pdf_dir,  f"{base}.pdf")

    _write_yaml(yaml_str, yaml_path)

    _section("Rendering PDF")
    print(f"  Role  : {args.role}  |  Theme: {theme_name}  |  Lang: {lang.value}")
    _render(yaml_path, pdf_path, theme_name)

    _section("Done")
    print(f"  PDF : {pdf_path}\n")


# ── JD MODE ────────────────────────────────────────────────────────────────────

def _run_jd_mode(args, cv: CVData, lang: Lang, ai) -> None:
    jd_text = _load_jd_text(args.jd)
    if not jd_text:
        sys.exit("Error: JD is empty.")

    theme_name   = _resolve_theme(args.theme)
    theme_config = load_theme_config(theme_name)

    print(f"\n  Model: {args.model}  |  Theme: {theme_name}  |  Lang: {lang.value}")

    print("\n  Analyzing job description...", end=" ", flush=True)
    jd_analysis = JDAnalyzer(ai).analyze(jd_text)
    print("done.")
    _section("JD Analysis")
    print(f"  Role     : {jd_analysis.role_title}")
    print(f"  Seniority: {jd_analysis.seniority}")
    print(f"  Required : {', '.join(jd_analysis.required_keywords[:6])}{'...' if len(jd_analysis.required_keywords) > 6 else ''}")

    print("\n  Scoring CV...", end=" ", flush=True)
    ats_result = ATSScorer(ai).score(cv, jd_analysis, lang)
    print("done.")
    _section("ATS Score")
    print(f"  Score  : {ats_result.score}/100")
    print(f"  Missing: {', '.join(ats_result.missing_keywords[:5]) or 'none'}")
    print(f"\n  {ats_result.summary[:200]}{'...' if len(ats_result.summary) > 200 else ''}")

    if not args.auto and not _confirm("Generate CV with this content?"):
        print("\n  Aborted.")
        return

    enricher         = ExperienceEnricher(ai)
    ranked_companies = None

    if theme_config.one_page:
        max_e = next((s.max_entries for s in theme_config.sections if s.key == "experience"), 8)
        print(f"\n  Generating summaries (one-page, top {max_e})...", end=" ", flush=True)
        ranked_companies, summaries = enricher.enrich_one_page(cv, jd_analysis, lang, max_e)
    else:
        print("\n  Generating summaries...", end=" ", flush=True)
        summaries = enricher.enrich(cv, jd_analysis, lang)
    print(f"done. ({len(summaries)} entries)")

    role_slug = _slugify(jd_analysis.role_title)
    profile   = Profile(
        name=role_slug,
        title=LocalizedString(es=ats_result.headline, en=ats_result.headline),
        summary=LocalizedString(es=ats_result.summary, en=ats_result.summary),
        ats_keywords=list(ats_result.ats_keywords),
        theme=theme_name,
    )

    yaml_str = generate_rendercv_yaml(cv, lang, theme_config, profile, summaries, ranked_companies)

    person        = _person_slug(cv)
    yaml_dir, pdf_dir = _output_dirs(person)
    os.makedirs(yaml_dir, exist_ok=True)
    os.makedirs(pdf_dir,  exist_ok=True)

    suffix    = "_one_page" if theme_config.one_page else ""
    base      = f"{person}_{role_slug}_{lang.value}{suffix}"
    yaml_path = os.path.join(yaml_dir, f"{base}.yaml")
    pdf_path  = os.path.join(pdf_dir,  f"{base}.pdf")

    _write_yaml(yaml_str, yaml_path)

    _section("Rendering PDF")
    print(f"  YAML : {yaml_path}")
    _render(yaml_path, pdf_path, theme_name)

    _section("Done")
    print(f"  PDF  : {pdf_path}")
    print(f"  Score: {ats_result.score}/100  |  Missing: {', '.join(ats_result.missing_keywords[:3]) or 'none'}\n")


# ── ENTRY POINT ────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    if args.create_person:
        _run_create_person(args.create_person)
        return

    if args.edit:
        cv_path = _find_cv_path(args.person)
        try:
            ai = build_ai_adapter(args.model)
        except ValueError as exc:
            sys.exit(f"Error: {exc}")
        _run_edit_mode(args, cv_path, ai)
        return

    if not args.lang:
        sys.exit("Error: --lang is required for --role and --jd modes.")

    cv_path = _find_cv_path(args.person)
    cv      = load_cv_data(cv_path)
    lang    = Lang(args.lang)

    try:
        ai = build_ai_adapter(args.model)
    except ValueError as exc:
        sys.exit(f"Error: {exc}")

    if args.role:
        _run_role_mode(args, cv, lang, ai, cv_path)
    else:
        _run_jd_mode(args, cv, lang, ai)


if __name__ == "__main__":
    main()
