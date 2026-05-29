# VitaeForge

> Job search assistant. One command, two modes. AI-powered CVs from a single data source.

VitaeForge treats a professional career as typed, versioned data. Give it a role or a job posting — it handles the rest: profile optimization, ATS scoring, experience enrichment, and PDF rendering.

---

## How It Works

```
                    ┌─────────────────────────────────────┐
                    │         vitaeforge (1 command)       │
                    └──────────────┬──────────────────────┘
                                   │
               ┌───────────────────┴────────────────────┐
               │                                        │
    ┌──────────▼──────────┐               ┌─────────────▼──────────┐
    │   --role <name>     │               │   --jd <file|url>      │
    │   Generic CV        │               │   Job-specific CV      │
    └──────────┬──────────┘               └─────────────┬──────────┘
               │                                        │
    Check cv.yaml hash                       Analyze JD with AI
    ↓ changed? → AI regenerates             Score CV (0-100)
    profile summary                          Enrich experience
               │                                        │
               └───────────────┬────────────────────────┘
                                │
                    cv_generator → rendercv YAML → PDF
```

---

## Architecture

Hexagonal (Ports & Adapters). Domain has zero external dependencies.

```
┌──────────────────────────────────────────────────┐
│                  ENTRYPOINTS                     │
│              src/entrypoints/cli.py              │
│       (the only entry point — main.py too)       │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│                 APPLICATION                      │
│            src/application/cv_generator.py       │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│                   DOMAIN                         │
│  models.py      ports/AIPort    use_cases/       │
│  ──────────     ─────────────   ─────────────    │
│  CVData                         JDAnalyzer       │
│  Experience                     ATSScorer        │
│  Profile                        ExperienceEnricher│
│  ThemeConfig                    ProfileGenerator  │
│  LocalizedString value_objects/ CVEditor         │
│  Lang (EN/ES)   JDAnalysis                       │
│                 ATSResult                        │
└──────────┬───────────────────────────┬───────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼───────────┐
│  INFRASTRUCTURE     │   │  INFRASTRUCTURE        │
│  ai/                │   │  persistence/loaders   │
│  ─────────────────  │   │  renderer/rendercv     │
│  openai_adapter     │   └────────────────────────┘
│  anthropic_adapter  │
│  google_adapter     │
│  ollama_adapter     │
│  factory + registry │
└─────────────────────┘
```

---

## Directory Structure

```
vitaeforge/
├── main.py                         # Direct entry point: python main.py --role ...
├── src/
│   ├── application/
│   │   └── cv_generator.py         # Assembles rendercv YAML
│   ├── domain/
│   │   ├── models.py               # CVData, Profile, ThemeConfig, Experience...
│   │   ├── ports/ai_port.py        # AIPort interface (abstract)
│   │   ├── use_cases/
│   │   │   ├── jd_analyzer.py      # Parses job descriptions
│   │   │   ├── ats_scorer.py       # Scores CV vs JD
│   │   │   ├── experience_enricher.py  # Generates ATS-optimized summaries
│   │   │   ├── profile_generator.py    # Generates generic role summaries
│   │   │   └── cv_editor.py        # Interactive editor: AI extraction + CAR bullets
│   │   └── value_objects/
│   │       ├── jd_analysis.py
│   │       └── ats_result.py
│   ├── entrypoints/
│   │   └── cli.py                  # Single entry point — both modes
│   └── infrastructure/
│       ├── ai/                     # OpenAI, Anthropic, Gemini, Ollama, Groq adapters
│       ├── persistence/
│       │   ├── loaders.py          # Reads cv.yaml, profile.yaml, theme.yaml
│       │   └── cv_writer.py        # Upsert/append write-back for --edit mode
│       └── renderer/rendercv_runner.py
│
├── people/
│   └── jane_doe/
│       ├── cv.yaml                 # Single source of truth for all career data
│       └── profiles/
│           ├── software_engineer__python_django_fastapi_aws.yaml
│           ├── data_engineer__python_aws.yaml
│           ├── technical_product_manager__python_aws.yaml
│           └── technical_project_manager__python_aws.yaml
│
├── themes/
│   ├── harmony/                    # One-page, two-column (Harmonize style)
│   │   ├── theme.yaml
│   │   ├── Header.j2.typ           # Sidebar: photo, contact, skills, education, languages
│   │   ├── Preamble.j2.typ
│   │   ├── SectionBeginning.j2.typ
│   │   ├── SectionEnding.j2.typ
│   │   └── entries/
│   │       ├── ExperienceEntry.j2.typ
│   │       └── EducationEntry.j2.typ
│   ├── moderncv/                   # Classic multi-page
│   └── globant/                    # Branded custom theme example
│
├── jobs/                           # Job description text files
│   ├── jd_data_engineer_remote.txt
│   ├── jd_project_manager_senior.txt
│   └── ...
│
├── generated/                      # Output — gitignored
│   └── jane_doe/
│       ├── yaml/                   # Intermediate rendercv YAMLs
│       └── pdf/                    # Final PDFs
│
├── tests/                          # 68 unit tests
├── .env                            # API keys — gitignored
├── .python-version                 # 3.12 — used by pyenv
├── pyproject.toml                  # Standard Python packaging (PEP 517)
└── requirements.txt
```

---

## Setup

### 1. Python via pyenv

```bash
pyenv install 3.12          # only needed once
pyenv local 3.12            # creates .python-version, auto-detected by pyenv
```

### 2. Virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .            # registers the `vitaeforge` command in the venv
```

### 4. API keys

Create `.env` in the project root (copy the template below):

```env
# AI model — must match an alias from the Available Models table
VITAEFORGE_MODEL=gpt-4o-mini

# Default theme — used when --theme is not passed and profile has no theme set
# Available: harmony, moderncv, globant
VITAEFORGE_THEME=moderncv

# API key for your chosen provider (add only the one you use)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...
# GROQ_API_KEY=...
```

**Theme resolution order:** `--theme` CLI flag → `VITAEFORGE_THEME` env → `theme:` in profile.yaml → `moderncv`

`VITAEFORGE_MODEL` is required. If omitted, the first model whose key is present in the environment is used.

### If you delete the venv

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

The project lives in `src/` — the venv only holds installed packages and the thin `vitaeforge` wrapper.

---

## Usage

There is **one command** with two modes. Run it as `vitaeforge` (venv activated) or `python main.py` (always works).

### Mode 1 — Generic CV by role

Generates a CV from a stored profile. Automatically detects if `cv.yaml` changed since the last run and refreshes the profile summary with AI if needed.

Role names follow the `role__tech_stack` convention — the double underscore separates the role from the tech specialization:

```bash
# Role only (no tech filter)
vitaeforge --role data_engineer --lang en

# Role + tech stack (AI anchors summary and skills to this stack)
vitaeforge --role software_engineer__python_django_fastapi_aws --lang en
vitaeforge --role data_engineer__python_aws --lang en

# Force profile refresh even if cv.yaml didn't change
vitaeforge --role data_engineer__python_aws --lang en --refresh

# Spanish version
vitaeforge --role software_engineer__python_django_fastapi_aws --lang es
```

The tech part is parsed into a stack list (`python_django_fastapi_aws` → `["Python", "Django", "FastAPI", "AWS"]`) and used to:
- Anchor Sentence 1 of the summary to the first tech's years of experience
- Restrict Sentence 3 (tech stack) to only the listed technologies
- Prioritize those technologies in per-entry experience descriptions

Available roles are whatever profile files exist under `people/<person>/profiles/`:
- `software_engineer__python_django_fastapi_aws`
- `data_engineer__python_aws`
- `technical_product_manager__python_aws`
- `technical_project_manager__python_aws`

### Mode 2 — Job-specific CV from a JD

Analyzes a job description, scores the CV, enriches experience bullets, and generates an optimized PDF.

```bash
# From a local file
vitaeforge --jd jobs/jd_project_manager_senior.txt --lang en

# From a URL
vitaeforge --jd https://linkedin.com/jobs/123 --lang en

# Specify model and skip confirmation
vitaeforge --jd jobs/jd_data_engineer_remote.txt --lang en --model gpt-4o-mini --auto

# Spanish CV for a specific posting
vitaeforge --jd jobs/jd_python_developer.txt --lang es --auto
```

### All options

```
vitaeforge (--role ROLE | --jd JD | --create-person NAME | --edit) [--lang {en,es}]
           [--person NAME]         Person folder under people/ (auto-detected if only one)
           [--theme THEME]         Theme override
           [--model MODEL]         AI model (default: from registry)
           [--refresh]             Force profile update — --role mode only
           [--auto]                Skip confirmation prompt
           [--overwritetheme]      Save --theme to profile.yaml — --role mode only
```

### Output

Both modes write to:
```
generated/<person>/yaml/<person>_<role>_<lang>[_one_page].yaml
generated/<person>/pdf/<person>_<role>_<lang>[_one_page].pdf
```

The `_one_page` suffix is added automatically when the active theme has `one_page: true` (e.g. harmony). This lets you keep both versions side by side:

```
jane_doe_data_engineer_en.pdf          ← moderncv (multi-page)
jane_doe_data_engineer_en_one_page.pdf ← harmony (one-page)
```

---

## Available Models

| Alias | Provider | Notes |
|-------|----------|-------|
| `gpt-4o` | OpenAI | Best quality |
| `gpt-4o-mini` | OpenAI | Fast, cost-effective |
| `claude-opus` | Anthropic | Highest reasoning |
| `claude-sonnet` | Anthropic | Balanced |
| `claude-haiku` | Anthropic | Fast |
| `gemini-pro` | Google | — |
| `gemini-flash` | Google | Fast, free tier |
| `groq-llama` | Groq | Fast, free tier |
| `ollama-llama3` | Ollama | Local, no API key needed |

Default model is set via `VITAEFORGE_MODEL` in `.env`. Fallback: first model whose key is present in the environment.

> `deepseek-chat` requires a paid API key — it returns 402 on the free tier. Use `groq-llama` or `gemini-flash` for a free alternative.

---

## Profile System

A profile file (`people/<person>/profiles/<role>.yaml`) defines the generic positioning for a target role. Profile names follow the `role__tech_stack` convention.

```yaml
name: software_engineer__python_django_fastapi_aws
title:
  en: Experienced Software Engineer Specializing in Python & Cloud Solutions
  es: Ingeniero de Software Experimentado Especializado en Python y Soluciones en la Nube
summary:
  en: "Jane Doe is a Software Engineer with 10 years of Python experience..."
  es: "Jane Doe es una Ingeniera de Software con 10 años de experiencia en Python..."
ats_keywords:
  - Python
  - Django
  - FastAPI
  - AWS
  - Docker
skill_tags: [software_engineer]    # which skill groups to show from cv.yaml
theme: harmony                     # which theme to use for this role
_meta:
  cv_hash: abc123def456            # auto-managed — set by vitaeforge on each run
profile_summaries:                 # auto-managed — cached per-language, per-role
  en:
    - company: Acme Corp
      start_date: "2024-01"
      ats_score: 90
      text: "Migrated a web app and database to AWS Lightsail, achieving a 90% cost
        reduction. Applied cloud architecture principles to deliver a scalable, cost-efficient solution."
```

`_meta.cv_hash` is written automatically by `vitaeforge --role`. If the hash of `cv.yaml` changes, both the profile summary and the per-entry summaries (`profile_summaries`) are invalidated and regenerated on the next run.

**Fields you manage manually:** `skill_tags`, `ats_keywords`, `theme`.
**Fields managed by AI:** `title`, `summary`, `profile_summaries` (regenerated when cv.yaml changes or `--refresh` is used).

### Role-differentiated summaries

The `role_label` parsed from the profile name (e.g. `"Software Engineer"` from `software_engineer__python_django_fastapi_aws`) is injected into every AI prompt. This ensures:

- **Profile summary Sentence 2** identifies and demonstrates capabilities specific to that role type — a Data Engineer summary highlights ETL reliability and pipeline accuracy; a Software Engineer summary highlights architecture decisions and delivery performance; a Technical PM summary highlights delivery velocity and stakeholder alignment.
- **Per-entry descriptions** (`profile_summaries`) answer "what does this experience prove about the candidate *as a `{role_label}`*?" — different angle for each role, from the same `cv.yaml`.

---

## Interactive CV Editor

`vitaeforge --edit` opens a menu-driven editor that writes directly to `cv.yaml`. No YAML knowledge required.

```bash
vitaeforge --edit
# With a specific person or AI model:
vitaeforge --edit --person jane_doe --model gemini-flash
```

```
──────────────────────────────────────────────────────────────
  VitaeForge CV Editor
──────────────────────────────────────────────────────────────
  CV: people/jane_doe/cv.yaml

  What would you like to add or update?

  1. Experience         (brain dump → AI extracts + CAR bullets)
  2. Project            (brain dump → AI extracts + CAR bullets)
  3. Skills             (brain dump → AI classifies)
  4. Education          (guided wizard)
  5. Language           (guided wizard)
  6. Course             (guided wizard)
  7. Certification      (guided wizard)
  8. Achievement        (one-liner)
  9. Review bullets     (pick experience → AI suggests improvements)
  0. Exit

  →
```

### How each option works

| Option | Input style | AI involved | Write strategy |
|--------|------------|-------------|---------------|
| **1 Experience** | Free-form brain dump | Yes — extracts structure + CAR bullets in es/en | Upsert by `(company, start_date)` |
| **2 Project** | Free-form brain dump | Yes — extracts structure + CAR bullets in es/en | Upsert by `name.en` |
| **3 Skills** | Comma/line list | Yes — normalizes + assigns domain tags | Merge by skill name |
| **4 Education** | Guided wizard | No | Upsert by `(institution, start_date)` |
| **5 Language** | Guided wizard | No | Upsert by `name.en` |
| **6 Course** | Guided wizard | No | Append (no dedup) |
| **7 Certification** | Guided wizard | No | Upsert by `credential_id` |
| **8 Achievement** | One-liner (es + en) | No | Append (no dedup) |
| **9 Review bullets** | Pick from list | Yes — CAR rewrites per bullet | Upsert the modified experience |

For brain-dump options (1, 2, 3), a YAML preview is shown after AI extraction. You confirm before anything is written.

For review bullets (option 9), each bullet is shown with its original and improved version side-by-side — you accept or keep the original one-by-one.

> **Note:** `cv.yaml` comments are not preserved on write-back (PyYAML limitation). This is an accepted trade-off — comments are in the scaffold template, not production data.

---

## Adding a New Person

```bash
# 1. Scaffold the person directory (placeholder data, no real PII)
vitaeforge --create-person jane_doe

# Output:
#   Created: people/jane_doe/cv.yaml
#   Created: people/jane_doe/profiles/
#
#   Next steps:
#     1. Edit people/jane_doe/cv.yaml with your real data
#     2. vitaeforge --person jane_doe --role <role> --lang en

# 2. Edit the generated cv.yaml with real data
#    The file includes inline comments explaining every field.

# 3. Generate the first CV — profile is created automatically on first run
vitaeforge --person jane_doe --role data_engineer__python_aws --lang en
```

The scaffold uses obviously fake data (`Jane Doe`, `jane.doe@example.com`, `+1 555 000 0000`) so no real PII is ever committed as a template. Profiles are auto-created by AI on the first `--role` run — no manual copy needed.

---

## Theme System

Each theme is a directory under `themes/` with:

| File | Purpose |
|------|---------|
| `theme.yaml` | Sections list, max entries/bullets per section, design config, `one_page` flag |
| `Header.j2.typ` | Rendered once — header/sidebar (name, contact, skills, languages) |
| `Preamble.j2.typ` | Typst document preamble (fonts, page size, custom functions) |
| `SectionBeginning.j2.typ` | Opens each content section |
| `SectionEnding.j2.typ` | Closes each content section |
| `entries/*.j2.typ` | One template per entry type (ExperienceEntry, EducationEntry…) |

### `theme.yaml` key fields

```yaml
theme_name: harmony
one_page: true          # activates ATS-ranked experience selection + paragraph highlights

sections:
  - key: experience
    name: Employment History
    max_entries: 8      # max entries shown (AI ranks by ATS relevance in one_page mode)
    max_bullets: 1      # bullets per entry (ignored in one_page mode — only summary shown)
  - key: entrepreneurship_experience
    name: Entrepreneurship
    optional: true
    max_entries: 3
```

### One-page behavior

When `one_page: true`:

- **Experience entries** show only the AI-generated summary paragraph (no bullets, no tools line).
- **Projects** show only `name + URL` — no dates, no category, no bullets. Space on a one-page CV is premium; the link is the "read more."
- **Experience pool** is ranked by ATS relevance and limited to `max_entries`.

Multi-page themes render projects in full (name, category, dates, bullets).

### Available themes

| Theme | Style | `one_page` |
|-------|-------|-----------|
| `harmony` | Two-column, white background, amber accent | yes |
| `moderncv` | Classic single-column | no |
| `globant` | Branded custom theme example | no |

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing
```

68 tests — domain models, use cases (including CVEditor), YAML generation, cv_writer upsert/append, CLI orchestration (all modes).

---

## cv.yaml Reference

```yaml
name: Jane
lastname: Doe
email: jane.doe@example.com
phone: "+1 555 000 0000"
website: https://dev.to/janedoe
linkedin: janedoe
github: janedoe
location:
  es: Ciudad, País
  en: City, Country

experience:
  - company: Acme Corp
    location:
      es: Lima, Perú
      en: Lima, Peru
    role:
      es: Ingeniero de Software Senior
      en: Senior Software Engineer
    start_date: "2023-01"
    end_date: "Present"           # or "2024-12"
    is_entrepreneurship: false    # true → goes to Entrepreneurship section
    description:                  # optional — shown in italics before highlights
      es: "Liderazgo técnico en migración cloud."
      en: "Technical leadership in cloud migration."
    aptitudes: [Python, Docker, AWS]
    bullets:
      - es: "Migré la arquitectura monolítica a microservicios."
        en: "Migrated monolithic architecture to microservices."

education:
  - institution: Example University
    location: { es: Ciudad, País, en: City, Country }
    degree:
      es: Ingeniería de Sistemas
      en: Systems Engineering
    start_date: "2015"
    end_date: "2019"
```

---

## CV Terminology

VitaeForge uses industry-standard CV writing terminology throughout its codebase and data schema. This avoids confusion with tool-specific naming conventions (e.g. rendercv calls its bullet-point field `highlights` internally, but that is its API name, not a semantic choice).

### Terminology map

| Term | Definition | Where it appears |
|------|-----------|-----------------|
| **highlight** | A career-level achievement block at the top of the CV — e.g. "Career Highlights" section listing 3-5 top accomplishments across the entire career. | Not a per-role concept. |
| **summary** | A brief prose description for a specific role — appears before bullet points for that experience entry. Rendered as plain text via rendercv's native `summary` field. | `profile_summaries` in profile.yaml; `summary:` in rendercv output. |
| **bullet** | A single achievement statement for a role, following the **CAR format** (Challenge → Action → Result). Rendered as a bulleted list item. | `bullets:` in `cv.yaml`; `Experience.bullets` in domain model; `highlights:` in rendercv output (rendercv's field name — infrastructure boundary). |

### CAR format for bullets

Each bullet should answer: **what was the challenge, what did you do, and what was the measurable result**.

```
✗ "Led the data engineering team."
✓ "Led a 4-person data engineering team to migrate 3 TB of legacy ETL jobs to AWS Glue, reducing pipeline failure rate by 40%."
```

### rendercv boundary

rendercv uses `highlights` as its YAML field name for bullet points. VitaeForge intentionally preserves this at the infrastructure boundary — `cv_generator.py` maps `exp.bullets` → `entry["highlights"]` when producing the rendercv YAML. This keeps the domain model clean without breaking the renderer.

### References

- **rendercv** — PDF/Typst CV renderer used as VitaeForge's rendering engine: [https://github.com/sinaatalay/rendercv](https://github.com/sinaatalay/rendercv)
- **Keep a Changelog** — changelog format standard: [https://keepachangelog.com](https://keepachangelog.com/en/1.0.0/)
- **LinkedIn Resume Builder** — industry reference for experience entry structure (role summary + bullets): [https://www.linkedin.com/help/linkedin/answer/a554998](https://www.linkedin.com/help/linkedin/answer/a554998)
- **The Muse — How to Write a Resume** — CAR format and bullet writing guidance: [https://www.themuse.com/advice/how-to-write-resume-bullet-points](https://www.themuse.com/advice/how-to-write-resume-bullet-points)
- **Harvard OCS Resume Guide** — authoritative reference on resume sections and terminology: [https://ocs.fas.harvard.edu/files/ocs/files/hes-resume-cover-letter-guide.pdf](https://ocs.fas.harvard.edu/files/ocs/files/hes-resume-cover-letter-guide.pdf)
- **Teal HQ — Resume Summary vs Objective** — distinction between career-level summary and role-level description: [https://www.tealhq.com/post/resume-summary](https://www.tealhq.com/post/resume-summary)

---

*VitaeForge — open source CV generation assistant*
