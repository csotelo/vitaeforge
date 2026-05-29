from dataclasses import dataclass


@dataclass(frozen=True)
class JDAnalysis:
    role_title: str
    seniority: str                    # junior | mid | senior | lead | director
    required_keywords: tuple[str, ...]
    preferred_keywords: tuple[str, ...]
    responsibilities: tuple[str, ...]
    raw_jd: str
