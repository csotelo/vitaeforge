---
title: "VitaeForge: Breaking the ATS Barrier"
published: true
description: I built VitaeForge to stop getting filtered out by ATS. Open-source CLI using hexagonal architecture, AI-powered ATS scoring, and CAR bullet generation. One command from cv.yaml to tailored PDF.
tags: python, ai, ats, career
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/bpcvhzfayb2ay6augv2o.png
published_at: 2026-05-29 17:00 +0000
---

**Open-source ATS Optimization Framework** | [**GitHub Repository**](https://github.com/csotelo/vitaeforge/)

---

## Abstract

**VitaeForge** is an open-source CLI tool that optimizes resumes for Applicant Tracking Systems (ATS). It takes a single career data file (`cv.yaml`) and a job description. It returns a tailored PDF with an ATS score, updated keywords, and CAR-formatted experience bullets.

The tool solves a specific problem: qualified candidates are filtered out by ATS before a human ever reads their resume. The cause is usually keyword mismatch and poor formatting — not a lack of qualifications.

VitaeForge addresses this through four mechanisms:

1. **Job description analysis** — extracts required and preferred keywords
2. **ATS scoring** — estimates keyword match before and after tailoring
3. **CAR formatting** — rewrites experience bullets in Challenge-Action-Result structure
4. **Hexagonal architecture** — supports multiple AI providers via a single interface

This paper documents the problem, the architecture, the development methodology, and the honest results from personal use.

---

## Executive Summary

**75% of resumes are rejected by ATS before a human reads them**[^1]. The reason is rarely lack of qualifications. It is keyword mismatch, bad formatting, and bullets that don't communicate impact clearly.

VitaeForge automates the fix:

- **Analyzes** the job description and extracts required keywords
- **Scores** the CV against the JD before and after tailoring
- **Rewrites** experience bullets in CAR format (Challenge-Action-Result)
- **Generates** a tailored PDF in under 2 minutes

It is open-source (MIT license). One command. One data file. Works with OpenAI, Anthropic, Google, Groq, and local Ollama models.

---

## 1. Introduction: The ATS Barrier

### 1.1 The Problem

**98% of Fortune 500 companies use ATS**[^3]. These systems filter resumes automatically before a recruiter sees them. Most candidates never know they were rejected by a machine.

I am a Python Developer with experience in cloud and data engineering. In early 2026, I was applying for jobs and getting no responses. My skills matched the job descriptions. But my resume scored **below 60/100** on ATS tools like Jobscan.

The problem was not my qualifications. It was three things:

| Problem | Cause | Example |
|---------|-------|---------|
| **Keyword mismatch** | ATS matches exact terms, not synonyms | "Docker Swarm" ≠ "Kubernetes" |
| **Bad formatting** | Tables and columns break ATS parsers | Multi-column layout renders as garbled text |
| **Weak bullets** | Generic statements don’t signal impact | "Led a team" vs. CAR-formatted bullet |

### 1.2 Why I Built VitaeForge

I built VitaeForge to solve my own problem. I wanted a tool that would:

- Read a job description and extract what the ATS is looking for
- Score my CV against those requirements
- Rewrite my experience bullets in CAR format
- Generate a tailored PDF in minutes, not hours

As a developer, I also used this project to practice **Product Owner and Technical PM skills**. I wrote user stories with Gherkin acceptance criteria, organized work into sprints, and used AI agents in role-specific modes (BA, Architect, QA, Engineer).

> *"I wasn’t just competing with other candidates — I was competing against algorithms designed to filter me out before a human ever saw my resume."*

---

## 2. How ATS Works — and Why Resumes Fail

### 2.1 The Numbers

| Statistic | Value | Source |
|-----------|-------|--------|
| Resumes rejected by ATS before human review | 75% | [Jobscan](https://www.jobscan.co/blog/ats-statistics/) |
| Fortune 500 companies using ATS | 98% | [Capterra](https://www.capterra.com/resources/what-is-an-applicant-tracking-system/) |
| Time a recruiter spends on initial resume review | 7 seconds | [Ladders](https://www.theladders.com/career-advice/eye-tracking-study-2018) |
| ATS pass rate improvement with CAR format | +38% | [The Muse](https://www.themuse.com/advice/how-to-write-resume-bullet-points) |

3 out of 4 resumes never reach a human. When they do, the reviewer spends 7 seconds.

![ATS rejection flow](https://mermaid.ink/img/Zmxvd2NoYXJ0IExSCiAgICBBW0NhbmRpZGF0ZSBzdWJtaXRzIHJlc3VtZV0gLS0-IEJbQVRTIHBhcnNlcyBkb2N1bWVudF0KICAgIEIgLS0-IEN7S2V5d29yZCBtYXRjaD99CiAgICBDIC0tPnxOb3wgRFvinYwgQXV0by1yZWplY3RlZF0KICAgIEMgLS0-fFllc3wgRXtGb3JtYXQgcmVhZGFibGU_fQogICAgRSAtLT58Tm98IEQKICAgIEUgLS0-fFllc3wgRntTY29yZSBhYm92ZSB0aHJlc2hvbGQ_fQogICAgRiAtLT58Tm98IEQKICAgIEYgLS0-fFllc3wgR1vinIUgUmVhY2hlcyBodW1hbiByZXZpZXdlcl0KICAgIEcgLS0-IEhbNyBzZWNvbmRzIG9mIGF0dGVudGlvbl0)

### 2.2 How ATS Screens Resumes

ATS systems filter candidates in three ways:

**1. Keyword matching** — exact terms, not synonyms.
```
JD requires:  "Kubernetes"
Resume says:  "Orchestrated containers using Docker Swarm"
ATS result:   ❌ Skill mismatch
```

**2. Format parsing** — complex layouts break the parser.
```
Resume table:   | Company | Role | Dates |
ATS output:     "Company Role Dates Acme Engineer 2020-2022"
```

**3. Impact scoring** — generic bullets don't signal value.

| Generic bullet | CAR-formatted bullet |
|----------------|----------------------|
| "Led a team of engineers." | **Challenge:** Missed deadlines due to unclear priorities. **Action:** Implemented Agile sprints. **Result:** Improved delivery time by 30%. |

A JD requiring "Python, Django, AWS" will reject a resume that says "Backend Development, REST APIs, Cloud" — even if the candidate is qualified.

### 2.3 What VitaeForge Changes

![VitaeForge Workflow Comparison](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/v5eq7icjum5pfdzbllmh.png)

| Metric | Without VitaeForge | With VitaeForge |
|--------|---------------------|-----------------|
| ATS Score (observed) | < 60 | 75–90 |
| Time per application | 20–40 minutes | < 2 minutes |
| Keyword alignment | Manual | Automated from JD |
| Bullet format | Generic | CAR (Challenge-Action-Result) |

---

## 3. Building VitaeForge: A Product Owner’s Journey

### 3.1 Methodology

Two disciplines shaped the development process:

**ATDD (Acceptance Test-Driven Development)**
I used the **ATDD skill for Claude Code** — not the full framework. It gave me the Gherkin/INVEST vocabulary and a role-switching discipline. Each feature started with acceptance criteria. The AI wrote code against those criteria. This reduced ambiguity and kept each session focused.

**Hexagonal Architecture (Ports & Adapters)**
Domain logic has zero external dependencies. AI providers, file I/O, and the PDF renderer are all infrastructure. The domain only knows about the `AIPort` interface. This made it trivial to swap models and test business logic in isolation.

![Domain architecture](https://mermaid.ink/img/Zmxvd2NoYXJ0IFRECiAgICBzdWJncmFwaCBEb21haW4KICAgICAgICBVQ1tVc2UgQ2FzZXNcbkFUU1Njb3JlciDCtyBFeHBlcmllbmNlRW5yaWNoZXJcbkpEQW5hbHl6ZXIgwrcgUHJvZmlsZUdlbmVyYXRvcl0KICAgICAgICBNW01vZGVsc1xuQ1ZEYXRhIMK3IEV4cGVyaWVuY2VcbkxvY2FsaXplZFN0cmluZ10KICAgICAgICBQW0FJUG9ydCBpbnRlcmZhY2VdCiAgICBlbmQKICAgIHN1YmdyYXBoIEluZnJhc3RydWN0dXJlCiAgICAgICAgT0FbT3BlbkFJIEFkYXB0ZXJdCiAgICAgICAgQUFbQW50aHJvcGljIEFkYXB0ZXJdCiAgICAgICAgR0FbR29vZ2xlIEFkYXB0ZXJdCiAgICAgICAgT0xbT2xsYW1hIEFkYXB0ZXJdCiAgICAgICAgUltyZW5kZXJjdiBSdW5uZXJdCiAgICAgICAgTFtZQU1MIExvYWRlcnNdCiAgICBlbmQKICAgIFAgLS0-IE9BICYgQUEgJiBHQSAmIE9MCiAgICBVQyAtLT4gUAogICAgVUMgLS0-IE0KICAgIFVDIC0tPiBSCiAgICBVQyAtLT4gTA)

### 3.2 Development Workflow

VitaeForge was built by one developer with AI assistants in role-specific modes. This is not an automated pipeline. It is deliberate context switching — each role gets its own session with its own constraints:

| Role | AI Tool | Primary Focus |
|------|---------|---------------|
| **Business Analyst** | Claude Sonnet (claude.ai) | User stories, Gherkin acceptance criteria |
| **Software Architect** | Claude Sonnet (Claude Code) | Hexagonal architecture, domain boundaries |
| **QA Engineer / Tester** | Mistral via OpenCode | Test case generation, edge case review |
| **Software Engineer** | Claude Sonnet (Claude Code) | Implementation, code quality |

Each role had its own prompt constraints:

| Role | Key constraint |
|------|----------------|
| BA | Gherkin only. No technical stack language. INVEST compliance. |
| Architect | Domain-first. No infrastructure imports in domain layer. |
| QA | Edge cases and failure paths only. No implementation suggestions. |
| Engineer | Architecture-compliant code only. Approved dependencies. No scope additions. |

Keeping roles separate prevented the model from drifting into solving adjacent problems. One long session with no role boundaries consistently produced worse results than shorter, focused sessions.

### 3.3 Process

Work was organized in short cycles. Each feature followed this sequence:

![Feature dev sequence](https://mermaid.ink/img/c2VxdWVuY2VEaWFncmFtCiAgICBwYXJ0aWNpcGFudCBCQSBhcyBCQSBSb2xlCiAgICBwYXJ0aWNpcGFudCBBcmNoIGFzIEFyY2hpdGVjdCBSb2xlCiAgICBwYXJ0aWNpcGFudCBFbmcgYXMgRW5naW5lZXIgUm9sZQogICAgcGFydGljaXBhbnQgUUEgYXMgUUEgUm9sZQogICAgQkEtPj5BcmNoOiBVc2VyIHN0b3J5ICsgR2hlcmtpbiBjcml0ZXJpYQogICAgQXJjaC0-PkVuZzogQXJjaGl0ZWN0dXJlIGFwcHJvYWNoICsgY29uc3RyYWludHMKICAgIEVuZy0-PlFBOiBJbXBsZW1lbnRhdGlvbgogICAgUUEtPj5Fbmc6IEZhaWx1cmVzIC8gZWRnZSBjYXNlcwogICAgRW5nLT4-UUE6IEZpeGVkIGltcGxlbWVudGF0aW9uCiAgICBRQS0tPj5CQTog4pyFIEFjY2VwdGFuY2UgY3JpdGVyaWEgcGFzcw)

1. Write acceptance criteria in Gherkin
2. Get architect review of the approach
3. Implement with the engineer role
4. Test and review output manually

**Definition of Ready** (before starting a story):
- Acceptance criteria written in Gherkin
- Architecture approach agreed
- Test scenarios defined

**Definition of Done** (before closing a story):
- Acceptance criteria pass
- CAR format verified on output
- PDF renders correctly

**Example acceptance test:**
```gherkin
Feature: Job Description Analysis
  Scenario: Extract keywords from a Python developer JD
    Given a job description for "Senior Python Developer" containing:
      """
      Must have: Python, Django, REST APIs.
      Preferred: Kubernetes, AWS, TDD.
      """
    When VitaeForge analyzes the job description
    Then it should return required keywords: ["Python", "Django", "REST APIs"]
    And preferred keywords: ["Kubernetes", "AWS", "TDD"]
```

**Testing:**

| Level | Tool | What is tested |
|-------|------|----------------|
| Unit | pytest | Domain models, use case logic, YAML generation |
| Integration | pytest | cv_writer upsert/append, CLI modes |
| Manual | Human review | AI-generated content before acceptance |

The project ships with **68 tests** total.

### 3.4 Model Selection

Models were selected based on personal experience during development and practical trade-offs between cost, quality, and availability. The project supports all models through a registry-based adapter pattern — any model can be swapped via the `VITAEFORGE_MODEL` environment variable without code changes.

| Alias | Provider | Used For | Personal Assessment |
|-------|----------|----------|---------------------|
| `claude-opus` | Anthropic | Development — all roles | **Best overall.** Handles any task complexity well — BA, architecture, coding. First choice when quality matters. |
| `claude-sonnet` | Anthropic | Development — coding + BA | **Strong for coding and requirements work.** Good balance of speed and quality. |
| `gpt-4o-mini` | OpenAI | Production default — **final choice** | **Reliable for structured output.** Cost-effective, consistent JSON. Tested for VitaeForge CV generation and stayed with this. |
| `gemini-flash` | Google | Production alternative — tested | **Works well for VitaeForge tasks.** Fast and free-tier friendly. Tested for CV generation; both GPT and Gemini performed well. |
| `groq-llama` | Groq | Testing / free-tier | **Acceptable for simple tasks.** Free and fast, but not suited to complex generation. |
| `ollama-mistral` | Ollama (local) | Small scoped tasks | **Only for narrow, simple tasks.** Struggles with multi-step reasoning or complex prompts. |
| `ollama-llama3` | Ollama (local) | Local/offline use | No API key required. |
| *BigPickle* (OpenCode Zen) | OpenCode Zen | ATDD dev role — specific tasks | **Limited use only.** Worked for very specific, well-scoped tasks when given detailed prompts and descriptions. Used as the developer agent in ATDD. Not suitable for open-ended or complex generation. |
| *Nemotron 2* (OpenCode Zen, free) | NVIDIA via OpenCode Zen | ATDD dev role — attempted | **Not recommended.** Did not produce usable output for development tasks. Free tier but not worth the tradeoff in quality. |

> **Author's note**: `claude-opus` was the best model across the board for development — BA, architecture, and implementation. `claude-sonnet` was the sweet spot for day-to-day coding and specification work. For production use of VitaeForge itself (generating CVs), both `gpt-4o-mini` and `gemini-flash` worked well; `gpt-4o-mini` was the final choice. BigPickle (OpenCode Zen) served for very specific, well-configured dev tasks; Nemotron 2 was not usable.

The registry (`src/infrastructure/ai/registry.py`) auto-detects the best available model from the environment if `VITAEFORGE_MODEL` is not set, using a priority order: `gpt-4o-mini` → `groq-llama` → `gemini-flash` → `claude-haiku` → `ollama-llama3`.

### 3.5 Technical Challenges and Solutions

The key challenges encountered during development are documented in Section 6. A brief summary here:

| Challenge | Root Cause | Solution Applied |
|-----------|-----------|-----------------|
| AI hallucination | Under-constrained prompts | Strict CONSTRAINT clauses + human review gates |
| Prompt scope creep | Open-ended sessions | Role-specific prompt contexts with explicit "DO NOT" clauses |
| ATS formatting fragility | Complex PDF layouts | Delegated to rendercv — VitaeForge only controls content |
| Multi-language consistency | Free-form translation | `LocalizedString` value object as core data primitive; lang passed explicitly in all prompts |
| CAR format compliance | Unstructured source bullets | Structured JSON output with separate `challenge`/`action`/`result` fields |

### 3.6 Lessons Learned

**1. Prompt quality beats model quality.**
A well-constrained prompt on `gemini-flash` produced better output than an open prompt on `claude-sonnet`. The most effective elements were explicit "DO NOT" clauses, a required output format, and source anchoring. Start there before upgrading the model.

![Prompt refinement loop](https://mermaid.ink/img/Zmxvd2NoYXJ0IFRECiAgICBBW0luaXRpYWwgUHJvbXB0XSAtLT4gQntPdXRwdXQgcXVhbGl0eT99CiAgICBCIC0tPnxHb29kfCBDW1VzZSBpbiBwcm9kdWN0aW9uXQogICAgQiAtLT58TWVkaXVtfCBEW0FkZCBjb25zdHJhaW50c10KICAgIEIgLS0-fFBvb3J8IEVbUmV2aXNlIHN0cnVjdHVyZV0KICAgIEQgLS0-IEZbQWRkIG91dHB1dCBmb3JtYXRdCiAgICBFIC0tPiBGCiAgICBGIC0tPiBC)

**2. Choose the right model for the task.**

| Model | Verdict |
|-------|---------|
| Claude Opus | Best overall. Handles BA, architecture, and coding well. Use when quality matters. |
| Claude Sonnet | Strong for coding and requirements work. Good daily driver. |
| GPT-4o-mini | Reliable for structured JSON output. Final choice for VitaeForge production. |
| Gemini Flash | Fast and free-tier friendly. Works well for CV generation. |
| Mistral (Ollama) | Only for narrow, simple tasks. Fails on multi-step reasoning. |
| BigPickle (OpenCode Zen) | Limited use. Needs very detailed prompts and narrow scope. |
| Nemotron 2 (OpenCode Zen) | Not recommended. Did not produce usable output. |

Start with a capable model. Downgrading to save cost is rational. Starting cheap to later upgrade wastes more time than it saves.

**3. Separate roles = less drift.**
One long session accumulates context and the model starts solving adjacent problems. Short sessions with one role per context produced consistently better results.

**4. Hexagonal architecture made model switching free.**
Changing AI provider required only a `.env` change. No code touched. This paid off every time an API limit was hit or a model underperformed.

**5. Human review is not optional for resume content.**
No prompt constraint fully eliminates hallucination. The `--jd` confirmation gate and `--edit` YAML preview exist so the author reviews every AI output before it is accepted.

**6. Delegate rendering, own content.**
Building a PDF renderer from scratch would have been a detour. Delegating to rendercv kept the focus on the real problem: content generation and ATS alignment.

---

## 4. Technical Implementation: Hexagonal Architecture and Core Components

### 4.1 Hexagonal Architecture Implementation

![VitaeForge Architecture Diagram](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/uh01q23sdbjqew832e4n.png)

VitaeForge uses hexagonal architecture (Ports & Adapters). Domain logic has no external dependencies. Infrastructure adapters connect to AI providers, files, and the renderer. The three layers are:

1. **Domain Layer** (`src/domain/`)
   - **Core Characteristics**: Complete isolation from external dependencies — no provider SDK imports, no file I/O, no rendering logic.
   - **Key Models** (Pydantic v2 BaseModel throughout):
     ```python
     # src/domain/models.py (actual)
     class LocalizedString(BaseModel):
         es: str
         en: str
         def get(self, lang: Lang) -> str:
             return self.es if lang == Lang.ES else self.en

     class Experience(BaseModel):
         company: str
         location: LocalizedString
         role: LocalizedString
         start_date: str
         end_date: str
         description: Optional[LocalizedString] = None
         aptitudes: List[str] = Field(default_factory=list)
         is_entrepreneurship: bool = False
         bullets: List[LocalizedString]

     class CVData(BaseModel):
         name: str
         lastname: str
         email: str
         phone: str
         location: LocalizedString
         experience: List[Experience]
         skills: List[SkillTag]
         education: List[Education]
         # ... certifications, courses, projects, languages, achievements
     ```
   - **Use Cases** (`src/domain/use_cases/`):
     - `jd_analyzer.py`: Extracts role title, seniority, required/preferred keywords, responsibilities from raw JD text
     - `ats_scorer.py`: Scores CV against JD via AI prompt, returns `ATSResult` with score + keyword gaps
     - `experience_enricher.py`: Rewrites experience bullets in CAR format, returns enriched `CVData`
     - `profile_generator.py`: Generates role-specific profile summary and per-entry summaries
     - `cv_editor.py`: Interactive menu-driven editor — brain dump → AI extraction → `cv.yaml` upsert

2. **Application Layer** (`src/application/cv_generator.py`)
   - Contains a single function `generate_rendercv_yaml()` that assembles domain objects into rendercv's YAML schema. It applies theme config (section selection, `max_entries`, one-page vs multi-page behavior) and produces a string ready for rendercv to consume.
   - No business logic lives here — it is pure assembly and serialization.

3. **Infrastructure Layer** (`src/infrastructure/`)
   - **AI adapters** (`src/infrastructure/ai/`): One class per provider, all implementing `AIPort.complete(prompt, system) -> str`. Providers: OpenAI, Anthropic, Google, Ollama, plus an OpenAI-compatible base used for Groq, DeepSeek.
   - **Persistence** (`src/infrastructure/persistence/`): `loaders.py` reads `cv.yaml`, `profile.yaml`, `theme.yaml`. `cv_writer.py` handles upsert/append write-back for `--edit` mode.
   - **Renderer** (`src/infrastructure/renderer/rendercv_runner.py`): Shells out to the `rendercv` CLI to convert the generated YAML to PDF.

The hexagonal architecture enables several critical capabilities:
- **Technology independence**: Core domain logic remains unchanged when upgrading AI models
- **Testability**: Each component can be tested in isolation
- **Adaptability**: New features can be added without modifying existing code
- **Maintainability**: Clear separation of concerns reduces cognitive load

### 4.2 Core Technical Features

The `--jd` mode end-to-end flow:

![JD end-to-end sequence](https://mermaid.ink/img/c2VxdWVuY2VEaWFncmFtCiAgICBwYXJ0aWNpcGFudCBDTEkKICAgIHBhcnRpY2lwYW50IEpEQSBhcyBKREFuYWx5emVyCiAgICBwYXJ0aWNpcGFudCBBVFMgYXMgQVRTU2NvcmVyCiAgICBwYXJ0aWNpcGFudCBFRSBhcyBFeHBlcmllbmNlRW5yaWNoZXIKICAgIHBhcnRpY2lwYW50IEdFTiBhcyBjdl9nZW5lcmF0b3IKICAgIHBhcnRpY2lwYW50IFJDViBhcyByZW5kZXJjdgogICAgQ0xJLT4-SkRBOiByYXcgSkQgdGV4dAogICAgSkRBLS0-PkNMSTogSkRBbmFseXNpcyAoa2V5d29yZHMsIHJvbGUsIHNlbmlvcml0eSkKICAgIENMSS0-PkFUUzogQ1ZEYXRhICsgSkRBbmFseXNpcwogICAgQVRTLS0-PkNMSTogQVRTUmVzdWx0IChzY29yZSwgbWF0Y2hlZCwgbWlzc2luZywgaGVhZGxpbmUpCiAgICBDTEktPj5DTEk6IFNob3cgc2NvcmUg4oaSIHVzZXIgY29uZmlybXMKICAgIENMSS0-PkVFOiBDVkRhdGEgKyBKREFuYWx5c2lzCiAgICBFRS0tPj5DTEk6IGVucmljaGVkIENWRGF0YSAoQ0FSIGJ1bGxldHMpCiAgICBDTEktPj5HRU46IGVucmljaGVkIENWRGF0YSArIHRoZW1lICsgcHJvZmlsZQogICAgR0VOLS0-PkNMSTogcmVuZGVyY3YgWUFNTAogICAgQ0xJLT4-UkNWOiBZQU1MIGZpbGUKICAgIFJDVi0tPj5DTEk6IFBERg)

#### 4.2.1 ATS Scoring System (`ats_scorer.py`)

The ATS scorer delegates evaluation entirely to the AI model. Rather than implementing local NLP (TF-IDF, cosine similarity), it sends a structured prompt containing CV facts and JD requirements, and receives back a JSON with score, matched keywords, missing keywords, and an optimized headline and summary. This design keeps the scoring logic in a single, swappable AI call rather than a brittle local pipeline:

```python
# src/domain/use_cases/ats_scorer.py (actual implementation)
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
```

The AI model returns:
- `score` — an integer 0–100 estimating ATS compatibility before tailoring
- `matched_keywords` — keywords present in both the CV and the JD
- `missing_keywords` — important JD keywords absent from the CV
- `headline` and `summary` — role-tailored replacements for the CV header

**Design rationale**: Using the language model as the scoring engine means the same model that understands natural language can also judge keyword semantic equivalence (e.g., "serverless" ≈ "AWS Lambda") without hand-crafted synonym maps. The trade-off is that the score is an estimate, not a deterministic calculation — which is honest, since real ATS scoring algorithms are also opaque.

#### 4.2.2 CAR Bullet Generation Engine (`experience_enricher.py`)

The `ExperienceEnricher` use case transforms experience bullets into Challenge-Action-Result format. It sends each bullet to the AI model with a structured prompt that requires JSON output with separate `challenge`, `action`, and `result` fields, then assembles them into a single coherent bullet string. The prompt includes the JD's required keywords so the model prioritizes relevant terminology in the result.

The CAR structure is:

![VitaeForge CAR System Framework](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/awdt0y56e17kuxp36may.png)

| Component | Description | Example |
|-----------|-------------|---------|
| **Challenge** | The business problem or context | "ETL pipeline had a 40% failure rate due to schema drift" |
| **Action** | Specific action taken | "Implemented schema validation layer with automated alerting" |
| **Result** | Measurable outcome | "Reduced pipeline failures by 35% and cut incident response time from 4h to 30min" |

The key prompt constraint is that the model must use **only information present in the original bullet**. It cannot invent metrics, extend timelines, or add skills not mentioned in the source. Human confirmation is required before any enriched output is accepted.

#### 4.2.3 Theme-Based Formatting (`cv_generator.py`)

`cv_generator.py` in the application layer maps domain objects to rendercv's YAML schema. The output format depends on the active theme's `one_page` flag:

```yaml
# themes/harmony/theme.yaml (actual)
theme_name: harmony
one_page: true
sections:
  - key: experience
    name: Employment History
    max_entries: 8      # AI-ranked by ATS relevance in one_page mode
    max_bullets: 1      # ignored in one_page mode — only summary shown
  - key: projects
    name: Projects
    optional: true
    max_entries: 3
```

**One-page mode** (`harmony`): experience entries show only the AI-generated summary paragraph. Projects show only `name + URL`. The experience pool is ranked by ATS relevance score and capped at `max_entries`.

**Multi-page mode** (`moderncv`, `globant`): full bullets, descriptions, tools line, and project details are included.

The `cv_generator.py` function `generate_rendercv_yaml()` handles all section rendering — there is no separate `LayoutEngine` class.

### 4.3 Incremental Regeneration

VitaeForge avoids unnecessary AI calls through a hash-based invalidation strategy. Every time `vitaeforge --role` runs, it computes a SHA hash of `cv.yaml` and stores it in the profile's `_meta.cv_hash` field. On subsequent runs, if the hash hasn't changed, the cached profile summary and per-entry `profile_summaries` are reused — no AI call is made.

![Hash cache flow](https://mermaid.ink/img/Zmxvd2NoYXJ0IFRECiAgICBBW3ZpdGFlZm9yZ2UgLS1yb2xlXSAtLT4gQltDb21wdXRlIFNIQSBoYXNoIG9mIGN2LnlhbWxdCiAgICBCIC0tPiBDe0hhc2ggbWF0Y2hlcyBfbWV0YS5jdl9oYXNoP30KICAgIEMgLS0-fFllc3wgRFtVc2UgY2FjaGVkIHN1bW1hcmllc1xuWmVybyBBSSBjYWxsc10KICAgIEMgLS0-fE5vfCBFW0NhbGwgQUkgZm9yIHByb2ZpbGUgc3VtbWFyeV0KICAgIEUgLS0-IEZbQ2FsbCBBSSBmb3IgZWFjaCBleHBlcmllbmNlIGVudHJ5XQogICAgRiAtLT4gR1tXcml0ZSBuZXcgaGFzaCArIHN1bW1hcmllcyB0byBwcm9maWxlLnlhbWxdCiAgICBEIC0tPiBIW2dlbmVyYXRlX3JlbmRlcmN2X3lhbWxdCiAgICBHIC0tPiBICiAgICBIIC0tPiBJW3JlbmRlcmN2IOKGkiBQREZd)

```yaml
# people/carlos_sotelo/profiles/data_engineer__python_aws.yaml
_meta:
  cv_hash: abc123def456       # updated automatically on each run
profile_summaries:            # per-entry AI summaries, keyed by (company, start_date)
  en:
    - company: Acme Corp
      start_date: "2024-01"
      ats_score: 90
      text: "Migrated a web app and database to AWS..."
```

This means:
- **First run for a role**: AI generates profile summary + per-entry summaries. Typical wall-clock time depends on the configured model and number of experience entries.
- **Subsequent runs (unchanged cv.yaml)**: Zero AI calls. Output is regenerated from cached YAML in under a second.
- **After editing cv.yaml**: Only changed or new entries trigger AI regeneration; existing cached summaries are preserved.

The `--refresh` flag bypasses the hash check and forces full regeneration when needed.

### 4.4 AI Adapter Architecture

VitaeForge uses a registry-and-factory pattern to decouple model selection from business logic. Every AI call in the domain layer goes through `AIPort` — an abstract interface. The infrastructure layer resolves the concrete adapter at startup from a central registry:

```python
# src/infrastructure/ai/factory.py (actual implementation)
def build_ai_adapter(model_alias: str | None = None) -> AIPort:
    alias = model_alias or DEFAULT_MODEL
    entry = REGISTRY.get(alias)           # ModelEntry: provider, model_id, env_key
    api_key = os.getenv(entry.env_key) if entry.env_key else None
    # Dispatch to the correct adapter class by provider
    if entry.provider == "anthropic":
        return AnthropicAdapter(entry.model_id, api_key)
    if entry.provider in ("openai", "openai_compat"):
        return OpenAICompatibleAdapter(entry.model_id, api_key, entry.base_url)
    if entry.provider == "google":
        return GoogleAdapter(entry.model_id, api_key)
    if entry.provider == "ollama":
        return OllamaAdapter(entry.model_id)
```

Adding a new AI provider requires only a new entry in `registry.py` and an adapter class — zero changes to domain or application code. This is the Open/Closed Principle applied directly to AI model management.

**Auto-detection fallback**: if `VITAEFORGE_MODEL` is not set, the factory iterates a priority list and selects the first model whose API key is present in the environment:

![Model fallback](https://mermaid.ink/img/Zmxvd2NoYXJ0IFRECiAgICBBW1N0YXJ0XSAtLT4gQntWSVRBRUZPUkdFX01PREVMIHNldD99CiAgICBCIC0tPnxZZXN8IENbVXNlIGNvbmZpZ3VyZWQgbW9kZWxdCiAgICBCIC0tPnxOb3wgRHtncHQtNG8tbWluaSBrZXkgcHJlc2VudD99CiAgICBEIC0tPnxZZXN8IEVbVXNlIGdwdC00by1taW5pXQogICAgRCAtLT58Tm98IEZ7Z3JvcS1sbGFtYSBrZXkgcHJlc2VudD99CiAgICBGIC0tPnxZZXN8IEdbVXNlIGdyb3EtbGxhbWFdCiAgICBGIC0tPnxOb3wgSHtnZW1pbmktZmxhc2gga2V5IHByZXNlbnQ_fQogICAgSCAtLT58WWVzfCBJW1VzZSBnZW1pbmktZmxhc2hdCiAgICBIIC0tPnxOb3wgSltDb250aW51ZSBkb3duIHByaW9yaXR5IGxpc3QuLi5d)

---

## 5. Observed Results

### 5.1 What the Tool Produces

This is a v1.0 release. Controlled empirical studies with statistical significance testing are outside the scope of this paper. What follows are honest observations from the author's personal use during the development period.

**ATS score behavior** (observed using Jobscan on personal applications):
- Resumes generated without VitaeForge (`--role` mode, generic tailoring) typically scored in the 55–70 range against specific JDs when tested on Jobscan.
- Resumes generated with `--jd` mode — which extracts required and preferred keywords from the JD and rebuilds the ATS keyword list and headline — consistently scored higher on the same tool, generally in the 75–90 range for roles that matched the candidate's actual background.
- The gap is expected: `--jd` mode explicitly targets the JD's terminology, while generic resumes use role-level positioning not tuned to a specific posting.

**Time per application**:
- Manual tailoring (editing bullets, rewriting summary, updating keywords for each posting): 20–40 minutes.
- VitaeForge `--jd` mode (one command, confirmation prompt, PDF output): under 2 minutes for a cached profile, slightly longer on first run depending on model response time.

**What the score actually measures**: VitaeForge's ATS score is the AI model's estimate of keyword overlap and alignment — not a Jobscan score, not access to any real ATS. It is a relative signal, useful for comparing two tailored versions of the same CV, not an absolute guarantee of ATS pass rate.

### 5.2 Personal Context

VitaeForge was built to solve a problem I was actively experiencing: my resume consistently scored below 60 on Jobscan for roles where I met the stated requirements. The gap was keyword terminology — I described my experience in general engineering language while job descriptions used stack-specific vocabulary (e.g., "Apache Airflow" vs "workflow orchestration", "Terraform" vs "infrastructure as code").

Building the tool changed how I approach applications:

1. **Targeted submissions**: I now check the ATS score before submitting. If the gap between my profile and the JD is large on missing keywords I genuinely have, `--jd` mode closes most of it automatically.
2. **Faster iteration**: What used to take 30 minutes per application (manual rewriting) now takes under 2 minutes, leaving time to write a better cover letter or research the company.
3. **Single source of truth**: All career data lives in `cv.yaml`. I edit once; every role variant regenerates from the same facts. No more copy-paste divergence between CV versions.

> *"The problem wasn't my qualifications — it was that my resume spoke human and the ATS was listening for keywords."*

This is a v1.0 tool. Broader empirical validation — tracking application outcomes across a larger sample, comparing ATS platforms, measuring interview conversion rates — is planned as the project matures and data accumulates.

## 6. Technical Challenges and Solutions

This section documents the real challenges encountered during development and the solutions actually implemented in the codebase.

### 6.1 AI Hallucination Control

**Challenge**: Language models occasionally invented non-existent skills, extended employment dates beyond what `cv.yaml` contained, or added achievements with no basis in the source data.

**Solution**: Strict constraint prompts with explicit "DO NOT" clauses and mandatory source anchoring. Every prompt that generates experience content includes:

```python
# Actual constraint pattern used throughout use_cases/
CONSTRAINTS = """
CONSTRAINTS:
- Use ONLY information contained in the provided CV data
- Do NOT invent skills, dates, companies, or metrics not present in the source
- Do NOT add achievements not supported by the input
- Return ONLY valid JSON — no explanation, no markdown wrapper
"""
```

**Verification**: Human review before accepting generated output. The `--jd` mode shows the ATS score and asks for confirmation before writing the PDF. The `--edit` mode shows a YAML preview before writing to `cv.yaml`. Both gates ensure a human sees the AI output before it becomes permanent.

### 6.2 ATS Formatting — Delegated to rendercv

**Challenge**: Resume formatting is one of the most common ATS failure points. Tables, multi-column layouts, embedded graphics, and non-standard fonts cause parsing errors in many ATS platforms.

**Solution**: VitaeForge does not generate PDF directly. It produces a structured YAML file consumed by [rendercv](https://github.com/sinaatalay/rendercv), which handles Typst-based PDF generation with ATS-compatible output. This delegation means VitaeForge inherits rendercv's formatting guarantees without reimplementing them.

The `cv_generator.py` application layer maps domain objects to rendercv's YAML schema. The only formatting decision VitaeForge makes is content selection and ordering — not layout rendering.

### 6.3 Domain-Infrastructure Decoupling

**Challenge**: AI providers change APIs, pricing, and availability. Hardcoding any provider into domain logic would make the system brittle and expensive to maintain.

**Solution**: The `AIPort` abstract interface in `src/domain/ports/` defines a single method: `complete(prompt, system) -> str`. Every use case depends only on this port. The concrete adapter (OpenAI, Anthropic, Google, Ollama) is resolved at startup by the factory and injected — the domain never imports any provider SDK.

This was validated in practice: switching the default model from `gpt-4o-mini` to `groq-llama` or `gemini-flash` requires only a `.env` change, with no code modification.

### 6.4 Multilingual Consistency

**Challenge**: Generating CV content in both English and Spanish from the same `cv.yaml` source requires consistent terminology and register across languages, particularly for technical terms.

**Solution**: The `LocalizedString` value object is the core data primitive — every user-visible string in the domain carries both `en` and `es` variants. AI generation prompts include the target language explicitly. Technical terms (stack names, tool names) are passed through unchanged since they don't translate (e.g., "Python", "Docker", "AWS" remain the same in both languages).

Human review remains the final quality gate — the author reviews both language outputs before submitting any application.

### 6.5 CAR Format Compliance

**Challenge**: Getting consistent Challenge-Action-Result format across all generated experience bullets, especially when the source material (`cv.yaml` bullets) is written in plain descriptive language.

**Solution**: The `ExperienceEnricher` use case uses a structured prompt that explicitly defines the CAR format and requires JSON output with separate `challenge`, `action`, and `result` fields. The application layer assembles these into a single coherent bullet. This forces the model to decompose the experience before composing the output, which produces more consistent results than asking for a free-form CAR bullet in one shot.

The `--edit` mode's "Review bullets" option (option 9) applies this same enrichment interactively, showing original and improved versions side-by-side for human acceptance.

## 7. Next Steps

This is v1.0. No formal roadmap exists. Two concrete improvements are planned.

### 7.1 Docker Image

**Problem**: Setup requires pyenv, Python 3.12, a virtualenv, `pip install`, and a `.env` file. That is five steps before running a single command.

**Goal**: One `docker run` that mounts `cv.yaml`, a JD file, and a `.env`, and produces a PDF.

```bash
# Target workflow
docker run --rm \
  -v $(pwd)/people:/app/people \
  -v $(pwd)/jobs:/app/jobs \
  -v $(pwd)/generated:/app/generated \
  --env-file .env \
  csotelo/vitaeforge --jd /app/jobs/my_jd.txt --lang en
```

**What this enables**:
- No local Python setup required
- Run on any machine or CI pipeline
- Consistent environment — no version mismatches
- Easier to share with non-technical users

The hexagonal architecture makes this straightforward. There are no database connections, no persistent state, and no background services. The container reads files, calls an AI API, and writes a PDF.

### 7.2 JD Scraping with Playwright

**Problem**: `--jd` currently accepts a local text file or a URL that returns plain text. Most real job postings are JavaScript-rendered pages (LinkedIn, Indeed, Greenhouse). Copy-pasting the JD manually is the current workaround.

**Goal**: Pass a job posting URL directly. VitaeForge fetches and extracts the description automatically.

```bash
# Current — manual copy-paste required
vitaeforge --jd jobs/my_jd.txt --lang en

# Planned — URL passed directly
vitaeforge --jd https://linkedin.com/jobs/view/12345 --lang en
```

**How it fits the architecture**: The `--jd` input is already abstracted in the CLI layer. A Playwright-based scraper would be a new infrastructure adapter — a `JDFetcherPort` in the domain, with a `PlaywrightAdapter` in infrastructure. The rest of the pipeline (JD analysis, ATS scoring, enrichment, PDF generation) stays unchanged.

**Key constraints for this feature**:
- Respect `robots.txt` and platform terms of service
- Fallback gracefully if a page cannot be scraped (prompt user to paste manually)
- Keep Playwright as an optional dependency — users who don't need scraping should not be required to install a browser

No timeline. No code written yet.

## 8. Conclusion

### 8.1 What VitaeForge Does

VitaeForge is a CLI tool. It takes a CV data file and a job description. It returns a tailored PDF with an ATS score and CAR-formatted bullets. It runs in under 2 minutes. It is open-source.

The core contributions of this v1.0 release:

| Contribution | Description |
|--------------|-------------|
| **Hexagonal architecture for AI tools** | Domain logic is fully isolated from AI providers. Swap models via `.env`. |
| **Prompt-based ATS scoring** | No local NLP. The AI estimates keyword gaps and generates tailored output in one call. |
| **CAR bullet generation** | Structured JSON prompt forces decomposition before composition. Consistent results. |
| **cv.yaml as single source of truth** | One file. Multiple role variants. Bilingual output. Hash-based caching. |
| **ATDD methodology for solo AI development** | Role-specific prompt sessions with explicit constraints. Documented and repeatable. |

### 8.2 Key Takeaways

- ATS filters 75% of resumes before a human reads them. The fix is keyword alignment and CAR formatting — not rewriting your career.
- Prompt engineering matters more than model selection. Constraints beat creativity.
- Hexagonal architecture pays off immediately when you need to swap AI providers.
- Human review is not optional. Always read what the AI generates before it goes on your CV.
- v1.0 is a working tool used in real job searches. It is not a prototype.

### 8.3 Try It

**For job seekers**: Copy a job description to a text file. Run `vitaeforge --jd jobs/my_jd.txt --lang en`. Check the ATS score. Submit the applications that score above 75.

**For developers**: Fork it. Add a provider adapter in 20 lines. Build a new theme. The architecture is designed for extension without modifying existing code.

> *"If ATS is the gatekeeper, VitaeForge is the key. Try it, fork it, or build on it — just don’t let algorithms decide your career."*

---

🔗 [**GitHub: github.com/csotelo/vitaeforge**](https://github.com/csotelo/vitaeforge/)

---

## Appendix

### A. ATS Statistics

| Statistic | Source |
|-----------|--------|
| 75% of resumes are rejected by ATS | [Jobscan](https://www.jobscan.co/blog/ats-statistics/) |
| 98% of Fortune 500 companies use ATS | [Capterra](https://www.capterra.com/resources/what-is-an-applicant-tracking-system/) |
| CVs with CAR format have 38% higher ATS pass rates | [The Muse](https://www.themuse.com/advice/how-to-write-resume-bullet-points) |

### B. License (MIT)

VitaeForge is licensed under the **MIT License**. Full text in [`LICENSE`](LICENSE).

---

### C. CLI Quick Reference

```bash
# Install
git clone https://github.com/csotelo/vitaeforge
cd vitaeforge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cp .env.example .env   # add your API key

# Mode 1 — Generic CV by role
vitaeforge --role data_engineer__python_aws --lang en
vitaeforge --role software_engineer__python_django_fastapi_aws --lang es
vitaeforge --role data_engineer__python_aws --lang en --refresh   # force AI regen

# Mode 2 — Job-specific CV from a JD file
vitaeforge --jd jobs/my_jd.txt --lang en
vitaeforge --jd jobs/my_jd.txt --lang en --model gemini-flash --auto

# Interactive CV editor
vitaeforge --edit
vitaeforge --edit --person jane_doe --model gpt-4o-mini

# Scaffold a new person
vitaeforge --create-person jane_doe
```

**All options:**

| Flag | Description |
|------|-------------|
| `--role ROLE` | Generate generic CV for a stored profile |
| `--jd FILE` | Generate job-specific CV from a JD text file |
| `--lang {en,es}` | Output language |
| `--person NAME` | Person folder under `people/` |
| `--model MODEL` | AI model alias (overrides `VITAEFORGE_MODEL`) |
| `--theme THEME` | Theme override (`harmony`, `moderncv`, `globant`) |
| `--refresh` | Force AI profile regeneration (ignores hash cache) |
| `--auto` | Skip confirmation prompt |
| `--edit` | Open interactive CV editor |
| `--create-person NAME` | Scaffold a new person directory |

**Available model aliases:**

| Alias | Provider | Free tier |
|-------|----------|-----------|
| `gpt-4o-mini` | OpenAI | No |
| `gpt-4o` | OpenAI | No |
| `claude-haiku` | Anthropic | No |
| `claude-sonnet` | Anthropic | No |
| `claude-opus` | Anthropic | No |
| `gemini-flash` | Google | Yes |
| `gemini-pro` | Google | No |
| `groq-llama` | Groq | Yes |
| `groq-mixtral` | Groq | Yes |
| `ollama-llama3` | Ollama (local) | Yes |
| `ollama-mistral` | Ollama (local) | Yes |

---

### D. Tools and Frameworks Used

| Tool | Role in VitaeForge | Link |
|------|--------------------|------|
| **rendercv** | PDF rendering engine — converts YAML to Typst PDF | [github.com/sinaatalay/rendercv](https://github.com/sinaatalay/rendercv) |
| **Pydantic v2** | Domain model validation and serialization | [docs.pydantic.dev](https://docs.pydantic.dev) |
| **Typer** | CLI framework | [typer.tiangolo.com](https://typer.tiangolo.com) |
| **PyYAML** | YAML read/write for `cv.yaml` and profiles | [pyyaml.org](https://pyyaml.org) |
| **pytest** | Unit and integration testing (68 tests) | [pytest.org](https://pytest.org) |
| **Jobscan** | ATS score validation during personal use | [jobscan.co](https://www.jobscan.co) |
| **Claude Code** | Primary development environment | [claude.ai/code](https://claude.ai/code) |
| **OpenCode Zen** | Secondary development tool (BigPickle, Nemotron 2) | [opencode.ai](https://opencode.ai) |

---

### E. Key References

| Reference | Relevance |
|-----------|-----------|
| Cockburn, A. — *Hexagonal Architecture* | Architectural pattern used in VitaeForge | [alistair.cockburn.us/hexagonal-architecture](https://alistair.cockburn.us/hexagonal-architecture/) |
| *ATDD by Example* — Gärtner, M. | ATDD methodology and Gherkin specification | [Manning](https://www.manning.com/books/atdd-by-example) |
| Harvard OCS Resume Guide | Resume terminology and CAR format guidance | [ocs.fas.harvard.edu](https://ocs.fas.harvard.edu/files/ocs/files/hes-resume-cover-letter-guide.pdf) |
| The Muse — *How to Write Resume Bullet Points* | CAR format +38% ATS pass rate source | [themuse.com](https://www.themuse.com/advice/how-to-write-resume-bullet-points) |
| Jobscan — *ATS Statistics* | 75% rejection rate source | [jobscan.co/blog/ats-statistics](https://www.jobscan.co/blog/ats-statistics/) |
| Capterra — *What is an ATS?* | 98% Fortune 500 usage source | [capterra.com](https://www.capterra.com/resources/what-is-an-applicant-tracking-system/) |
| The Ladders — *Eye Tracking Study* | 7-second recruiter review source | [theladders.com](https://www.theladders.com/career-advice/eye-tracking-study-2018) |
| csotelo — *LangGraph + ATDD Pipeline* | Prior article: multi-agent ATDD methodology | [dev.to/csotelo](https://dev.to/csotelo/building-a-multi-agent-atdd-pipeline-with-langgraph-and-hexagonal-architecture-5a9k) |