# Changelog

All notable changes to the **VitaeForge** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.11.0] - 2026-05-20
### Fixed
- **Harmony `OneLineEntry` overlap bug**: created `themes/harmony/entries/OneLineEntry.j2.typ` with explicit `#block()` per entry and `#v(space_between_text_based_entries)` spacing. Built-in rendercv template (`{{entry.main_column}}` with no spacing) caused all OneLineEntry items to render on top of each other.

## [2.10.0] - 2026-05-20
### Changed
- **One-page projects: title + URL only** — when `theme_config.one_page` is true, `generate_rendercv_yaml()` renders projects as `OneLineEntry` (`{"label": name, "details": url}`) instead of the full ExperienceEntry format. Dates, category, and bullets are omitted — consistent with expert guidance that on a one-page CV the link is the "read more" and bullets waste space.

## [2.9.0] - 2026-05-20
### Added
- **`role__tech_stack` profile naming convention** — double underscore separates the role from the technology specialization (e.g. `software_engineer__python_django_fastapi_aws`, `data_engineer__python_aws`). Tech-free role names remain valid (`data_engineer`).
- **`_parse_role_name(role)`** in `cli.py` — parses the convention into `(role_label, tech_stack)`: role label is title-cased (`"Software Engineer"`), tech stack is a normalized list (`["Python", "Django", "FastAPI", "AWS"]`).
- **`_TECH_ALIASES`** dict — normalizes common abbreviations: `fastapi→FastAPI`, `aws→AWS`, `sql→SQL`, `gcp→GCP`, `api→API`, `cqrs→CQRS`, `dbt→dbt`, `etl→ETL`, and more.
- **`role_label` parameter** added to all three `ProfileGenerator` methods (`create_new_profile`, `generate`, `generate_profile_summaries`) and all three prompts (`_NEW_PROFILE_PROMPT`, `_PROMPT`, `_SUMMARIES_PROMPT`).
### Changed
- **Role-differentiated profile summaries** — Sentence 2 of the profile summary now instructs the AI to first identify the 2-3 core capabilities specific to the `{role_label}` (inferred from the role name), then find evidence of those capabilities across different time periods. Previously used a generic "consistent pattern of excellence" instruction that produced identical content across roles.
- **Role-differentiated per-entry descriptions** (`_SUMMARIES_PROMPT` instruction 3) — changed from "key skill that maps to the target role" to "the SPECIFIC `{role_label}` capability this experience demonstrates — answer 'what does this entry prove about the candidate AS A `{role_label}`?'" Each entry must highlight a different, role-specific angle.
- **`generate_profile_summaries`** now receives `tech_stack` and injects a tech focus hint into `_SUMMARIES_PROMPT` so the second sentence of each entry description prioritizes the role's tech stack.
- All four cached `profile_summaries` sections invalidated to force regeneration with role-differentiated prompts.
- `README.md`: usage examples, directory structure, profile system, and theme system sections updated to reflect the `role__tech_stack` convention and one-page behavior.

## [2.8.0] - 2026-05-19
### Added
- **`vitaeforge --edit`** interactive CV editor — add or update any CV section without touching YAML manually:
  - **Experience** (option 1): brain-dump free-form text → AI extracts company, role, dates, location, tools, and writes CAR-format bullets in English and Spanish in a single call.
  - **Project** (option 2): brain-dump → AI extracts name, URL, category (`open_source`, `activism`, `community`), dates, and CAR bullets.
  - **Skills** (option 3): paste any list → AI normalizes, de-duplicates, and assigns domain tags (`software_engineer`, `data_engineer`, `technical_product_owner`, `all`).
  - **Education** (option 4): guided wizard — institution, location, degree, dates.
  - **Language** (option 5): guided wizard — name and proficiency level in both languages.
  - **Course** (option 6): guided wizard — name, issuer, date. No credential ID (use Certification for that).
  - **Certification** (option 7): guided wizard — name, issuer, date, `credential_id` (required), optional URL, category.
  - **Achievement** (option 8): one-liner — non-credentialed recognition, community role, or extracurricular activity.
  - **Review bullets** (option 9): select any experience entry → AI reviews each bullet and proposes an improved CAR version; accept or keep original one-by-one.
  - After every AI extraction, a YAML preview is shown before any write is performed.
  - All changes are written back to `cv.yaml` via upsert (no duplicates). Upsert keys: experience `(company, start_date)`, project `name.en`, education `(institution, start_date)`, skill name, language `name.en`, certification `credential_id`. Courses and achievements are append-only.
- **`src/domain/use_cases/cv_editor.py`** — `CVEditor` use case with four AI-powered methods: `extract_experience`, `extract_project`, `classify_skills`, `review_bullets`. All prompts produce bilingual output (es/en) in one call.
- **`src/infrastructure/persistence/cv_writer.py`** — eight write-back helpers: `upsert_experience`, `upsert_project`, `upsert_education`, `upsert_skills`, `upsert_language`, `upsert_certification`, `append_course`, `append_achievement`. Load → mutate → write cycle; comments in `cv.yaml` are not preserved (PyYAML limitation — acceptable trade-off).
- 15 new tests in `tests/test_editor.py` covering all `CVEditor` methods and all `cv_writer` upsert/append functions. Total test count: **68**.

## [2.7.0] - 2026-05-19
### Added
- **`--create-person <name>`** mode: scaffolds `people/<name>/cv.yaml` and `people/<name>/profiles/` with placeholder data and inline comments. No PII is used as template — fake data (`Jane Doe`, `jane.doe@example.com`) ensures real personal data is never accidentally committed as an example.
- `_CV_SCAFFOLD` constant in `cli.py`: the annotated cv.yaml template, with one-line comments on every field explaining purpose and format.
- `_run_create_person()` function: validates the target does not exist, creates the directory tree, writes the scaffold, and prints actionable next steps.
- `--lang` is now optional at the argparse level (validated only for `--role` / `--jd` modes, not required for `--create-person`).
### Changed
- `README.md`: "Adding a New Person" section replaced — `cp` instruction removed, `--create-person` documented with full output and next steps.
- `All options` usage block updated to reflect the three modes and corrected flags.

## [2.6.0] - 2026-05-19
### Changed
- **Standard CV terminology adopted** throughout the codebase (see [CV Terminology](#) in README):
  - `Experience.highlights` → `Experience.bullets` (domain model field)
  - `highlights:` in `cv.yaml` → `bullets:` (data schema key)
  - `ThemeSection.max_highlights` → `ThemeSection.max_bullets`
  - `max_highlights:` in `theme.yaml` → `max_bullets:`
  - `profile_highlights` in profile.yaml → `profile_summaries`
  - `generate_profile_highlights()` → `generate_profile_summaries()`
  - `_highlight_key()` → `_experience_key()`
  - `enrichments` parameter in `generate_rendercv_yaml()` → `summaries`
- **One-page behavior corrected**: one-page themes now render only the `summary` field per role (AI-generated prose) with no bullet list — consistent with the distinction between *summary* (role-level prose) and *bullets* (achievement list items). Previously the AI text was incorrectly inserted as the first bullet.
- rendercv output YAML continues to use `highlights` as the field key — this is rendercv's API and is intentionally preserved at the infrastructure boundary.

## [2.5.0] - 2026-05-19
### Changed
- **Consolidated to a single command**: `vitaeforge` replaces `vitaeforge`, `vitaeforge-batch`, and `vitaeforge-profile`.
- New `--role <name>` mode: generates a generic CV from a stored profile; auto-detects `cv.yaml` changes via SHA-256 hash and refreshes profile summary with AI when needed. Use `--refresh` to force.
- New `--jd <file|url>` mode: full JD-optimized pipeline (JDAnalyzer → ATSScorer → ExperienceEnricher → PDF). Supports local files and HTTP/HTTPS URLs.
- `ProfileGenerator` use case absorbed into `cli.py` role flow — no longer a separate entrypoint.
- Batch regeneration absorbed into `--role` mode — run once per role instead of a separate command.
### Removed
- `src/entrypoints/batch.py` — superseded by `--role` mode.
- `src/entrypoints/profile_cli.py` — superseded by `--role` mode with auto-refresh.
- `vitaeforge-batch` and `vitaeforge-profile` script registrations from `pyproject.toml`.
### Added
- `main.py` at project root — direct entry point via `python main.py`, independent of venv scripts.
- `.python-version` file for pyenv (`3.12`).
- `requirements.txt` for standard `pip install` workflow (no uv required).
- `_meta.cv_hash` written to profile YAML on each `--role` run to track `cv.yaml` state.

## [2.4.0] - 2026-05-19
### Changed
- Harmony theme: Education section moved to left sidebar (best-practice placement for 5+ years experience profiles).
- Harmony theme: Increased `space_below` for section titles (0.16cm → 0.28cm) for better visual breathing room.
- Harmony ExperienceEntry: Removed bullet `•` from highlights — paragraphs are narrative, not list items.
- One-page AI prompt: Highlights expanded to 2-3 sentences / max 55 words (previously 2 sentences / max 40 words).

## [2.3.0] - 2026-05-19
### Added
- `one_page` mode in harmony theme: AI selects top N ATS-relevant experiences and generates one paragraph highlight per entry.
- `ExperienceEnricher.enrich_one_page()`: ranks experiences by ATS score, generates 2-3 sentence paragraphs instead of single bullet.
- `entrepreneurship_experience` section in harmony theme (optional, max 3 entries, separate from Employment History).
- `ThemeConfig.one_page: bool` field in domain model.
- `generate_rendercv_yaml()` now accepts `ranked_companies` to reorder experience pool by ATS relevance.
- CLI automatically routes to `enrich_one_page()` when `theme_config.one_page=True`.
### Changed
- Harmony `max_highlights: 1` — one paragraph per experience entry.
- Harmony `max_entries: 8` for employment (up from 5).
- Enrichment paragraphs no longer wrapped in `**bold**` markdown.

## [2.2.0] - 2026-05-18
### Changed
- Harmony ExperienceEntry: position rendered bold, company in lighter gray — matches Harmonize visual hierarchy.
- Date/location display: date first, location second, separated by `·`.
- Harmony Header: phone `tel:` URI prefix stripped and dashes replaced with spaces for clean display.
- `cv.website` cast to string via `| string` Jinja2 filter before URL manipulation (Pydantic HttpUrl fix).
- Sidebar in harmony: removed gray background, pure white layout matching Harmonize template.

## [2.1.0] - 2026-05-17
### Added
- **Harmony theme** (`themes/harmony/`): Two-column visual template inspired by resume.io Harmonize.
  - Amber/gold accent color `rgb(198,138,42)` throughout.
  - Left sidebar: circular photo, name, headline, Details (contact), Skills by category, Languages with dot indicators, Education.
  - Right column: Profile summary, Employment History, Entrepreneurship, Education (now sidebar).
  - Section titles: 13pt regular amber with thin amber underline.
  - Custom `ExperienceEntry.j2.typ` and `EducationEntry.j2.typ`.
  - Sidebar sections (skills, languages, education, certifications, courses) suppressed from right column via `SectionBeginning.j2.typ`.
- `cv.headline` propagated to rendercv YAML when profile has a title.

## [2.0.0] - 2026-04-01
### Added
- **Complete hexagonal architecture rewrite** — `src/` layout with four layers:
  - `domain/`: Pure business logic — `models.py`, ports, use cases, value objects.
  - `application/`: Orchestration — `cv_generator.py` produces rendercv YAML from domain objects.
  - `infrastructure/`: Adapters — AI (OpenAI, Anthropic, Gemini, Ollama), persistence loaders, rendercv runner.
  - `entrypoints/`: Driving adapters — `cli.py` (interactive), `batch.py` (regenerate all profiles).
- **AI pipeline** (three use cases):
  - `JDAnalyzer`: parses job description → role title, seniority, keywords, responsibilities.
  - `ATSScorer`: scores CV against JD, identifies gaps, generates summary and headline.
  - `ExperienceEnricher`: generates ATS-optimized bridge bullets or paragraphs per experience.
- **Multi-model AI support** via `AIPort` abstraction: OpenAI (gpt-4o, gpt-4o-mini), Anthropic (claude-*), Google (gemini-flash, gemini-pro), Ollama (local), Groq (llama).
- **Theme system**: each theme is a directory with `theme.yaml` (sections config + design defaults) + Typst/Jinja2 templates.
- **Profile system**: `people/<person>/profiles/<profile>.yaml` — pre-built profiles for each target role.
- **`vitaeforge` CLI**: `--jd`, `--cv`, `--lang`, `--theme`, `--model`, `--auto` flags.
- **`vitaeforge-batch`**: regenerates all profile YAMLs for a person without AI (uses stored profile summaries).
- **53 unit tests** with pytest, 100% coverage on domain and application layers.
- `ThemeSection` model: `key`, `name`, `optional`, `max_entries`, `max_highlights`, `requires_profile`.
- `ThemeConfig` model: `theme_name`, `sections`, `design`, `one_page`.
### Removed
- Legacy `main.py`, `data_loader.py`, `models.py` (root-level) — replaced by hexagonal `src/` layout.
- `cv_data.yaml` (root-level) — data now lives under `people/<person>/cv.yaml`.
- `output/` directory — replaced by `generated/<person>/yaml/` and `generated/<person>/pdf/`.

---

## [1.0.14] - 2026-01-28
### Added
- Created `CHANGELOG.md` to track project evolution and architectural decisions.

## [1.0.13] - 2026-01-27
### Changed
- Updated `README.md` to reflect the new **VitaeForge** identity.
- Refined project documentation with Clean Architecture specifications.

## [1.0.12] - 2026-01-26
### Added
- New Domain Models: `Education` and `Course`.
- Support for "Truncated" or "Incomplete" academic records.
- Support for Professional Courses with issuer and date tracking.
### Fixed
- Resolved `engineering` theme validation errors by ensuring stable theme mapping.

## [1.0.11] - 2026-01-25
### Added
- Integrated **VitaeForge** Engine Signature and metadata in generated YAMLs.
- Automatic injection of repository link in the CV footer/sections.

## [1.0.10] - 2026-01-24
### Added
- Smart Chronological Sorting: Roles marked as "present" are prioritized at the top.
- Multi-field sorting logic (Tuples) for nested dates.
### Fixed
- Date normalization layer: Case-insensitive "present" sanitization for RenderCV compliance.

## [1.0.9] - 2026-01-23
### Added
- Refactored Experience Model: Added `is_entrepreneurship` flag.
- Automatic section splitting: Career vs. Entrepreneurship in generated YAML.
- Enhanced Certification Model: Split Professional vs. Extracurricular categories.
- High-fidelity data sync: Added `description` and `aptitudes` support per job entry.

## [1.0.8] - 2026-01-22
### Changed
- Decoupled Tests from File System: Tests now use `mock_open` and memory strings.
- Removed dependency on physical `cv_data.yaml` for unit testing.
- Achieved 100% Coverage on logical units in isolation.

## [1.0.7] - 2026-01-21
### Added
- YAML Data Source implementation: Migrated content to `cv_data.yaml`.
- Created `data_loader.py` Repository Layer.
- Implemented `output/` directory for artifact isolation and cross-language suffix support.

## [1.0.6] - 2026-01-20
### Changed
- Modularized project into Clean Architecture layers: `models.py`, `main.py`.
- Separated Domain Entities from Execution Logic.

## [1.0.5] - 2026-01-19
### Added
- Synchronized experience data with official PDF records.
- Improved Spanish/English translations for historical job roles.

## [1.0.4] - 2026-01-18
### Fixed
- RenderCV YAML Schema validation: Removed legacy keys (`font`, `page_size`, `color`).
- Standardized theme usage to `moderncv`.

## [1.0.3] - 2026-01-17
### Added
- Integrated `rendercv[full]` dependency via `uv`.
- Improved Developer Experience (DX) with dynamic CLI instructions in `main.py` output.

## [1.0.2] - 2026-01-16
### Added
- Initial Unit Test suite with PyUnit.
- Achieved 100% Coverage using `runpy` to test script entry points.

## [1.0.1] - 2026-01-15
### Added
- Integrated `uv` for lightning-fast and reproducible dependency management.
- Created initial `pyproject.toml` and basic project documentation.

## [1.0.0] - 2026-01-14
### Added
- Initial Release of `cv_engine.py`.
- Core i18n logic using Pydantic and `LocalizedString` pattern.
