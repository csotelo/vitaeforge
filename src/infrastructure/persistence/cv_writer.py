"""
Write-back helpers for cv.yaml.

All functions load the raw YAML dict, apply an upsert or append, then write
the file back. PyYAML does not preserve comments — this is acceptable.

Upsert keys:
  experience    → (company, start_date)
  project       → name.en
  education     → (institution, start_date)
  skill         → skill name
  language      → name.en
  certification → credential_id
  course        → (name.en, issuer)
  achievement   → exact text (es+en)
"""

import yaml


def _load(cv_path: str) -> dict:
    with open(cv_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save(cv_path: str, data: dict) -> None:
    with open(cv_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


# ── Experience ────────────────────────────────────────────────────────────────

def upsert_experience(cv_path: str, entry: dict) -> bool:
    """Upsert by (company, start_date). Returns True if replaced, False if appended."""
    data = _load(cv_path)
    experiences = data.setdefault("experience", [])
    key = (entry.get("company", ""), entry.get("start_date", ""))
    for i, exp in enumerate(experiences):
        if (exp.get("company", ""), exp.get("start_date", "")) == key:
            experiences[i] = entry
            _save(cv_path, data)
            return True
    experiences.append(entry)
    _save(cv_path, data)
    return False


# ── Project ───────────────────────────────────────────────────────────────────

def upsert_project(cv_path: str, entry: dict) -> bool:
    """Upsert by name.en. Returns True if replaced, False if appended."""
    data = _load(cv_path)
    projects = data.setdefault("projects", [])
    name_en = (entry.get("name") or {}).get("en", "")
    for i, p in enumerate(projects):
        if (p.get("name") or {}).get("en", "") == name_en:
            projects[i] = entry
            _save(cv_path, data)
            return True
    projects.append(entry)
    _save(cv_path, data)
    return False


# ── Education ─────────────────────────────────────────────────────────────────

def upsert_education(cv_path: str, entry: dict) -> bool:
    """Upsert by (institution, start_date). Returns True if replaced, False if appended."""
    data = _load(cv_path)
    education = data.setdefault("education", [])
    key = (entry.get("institution", ""), entry.get("start_date", ""))
    for i, edu in enumerate(education):
        if (edu.get("institution", ""), edu.get("start_date", "")) == key:
            education[i] = entry
            _save(cv_path, data)
            return True
    education.append(entry)
    _save(cv_path, data)
    return False


# ── Skills ────────────────────────────────────────────────────────────────────

def upsert_skills(cv_path: str, new_skills: list[dict]) -> tuple[int, int]:
    """Merge skills by name. Returns (added, updated) counts."""
    data = _load(cv_path)
    existing = data.setdefault("skills", [])
    index = {s.get("skill", "").lower(): i for i, s in enumerate(existing)}
    added = updated = 0
    for sk in new_skills:
        name = sk.get("skill", "")
        if name.lower() in index:
            existing[index[name.lower()]] = sk
            updated += 1
        else:
            existing.append(sk)
            index[name.lower()] = len(existing) - 1
            added += 1
    _save(cv_path, data)
    return added, updated


# ── Language ──────────────────────────────────────────────────────────────────

def upsert_language(cv_path: str, entry: dict) -> bool:
    """Upsert by name.en. Returns True if replaced, False if appended."""
    data = _load(cv_path)
    languages = data.setdefault("languages", [])
    name_en = (entry.get("name") or {}).get("en", "")
    for i, lang in enumerate(languages):
        if (lang.get("name") or {}).get("en", "") == name_en:
            languages[i] = entry
            _save(cv_path, data)
            return True
    languages.append(entry)
    _save(cv_path, data)
    return False


# ── Course ────────────────────────────────────────────────────────────────────

def append_course(cv_path: str, entry: dict) -> None:
    """Append course (no dedup — user may have taken similar courses from different issuers)."""
    data = _load(cv_path)
    data.setdefault("courses", []).append(entry)
    _save(cv_path, data)


# ── Certification ─────────────────────────────────────────────────────────────

def upsert_certification(cv_path: str, entry: dict) -> bool:
    """Upsert by credential_id. Returns True if replaced, False if appended."""
    data = _load(cv_path)
    certs = data.setdefault("certifications", [])
    cid = entry.get("credential_id", "")
    for i, c in enumerate(certs):
        if c.get("credential_id", "") == cid:
            certs[i] = entry
            _save(cv_path, data)
            return True
    certs.append(entry)
    _save(cv_path, data)
    return False


# ── Achievement ───────────────────────────────────────────────────────────────

def append_achievement(cv_path: str, entry: dict) -> None:
    """Append achievement (no dedup)."""
    data = _load(cv_path)
    data.setdefault("achievements", []).append(entry)
    _save(cv_path, data)
