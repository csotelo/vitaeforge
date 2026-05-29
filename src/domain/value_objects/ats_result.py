from dataclasses import dataclass


@dataclass(frozen=True)
class ATSResult:
    headline: str                     # generated tagline for this specific JD
    summary: str                      # generated career summary tailored to JD
    ats_keywords: tuple[str, ...]     # keywords to feature prominently
    score: int                        # 0-100 estimated ATS match
    matched_keywords: tuple[str, ...]
    missing_keywords: tuple[str, ...]
