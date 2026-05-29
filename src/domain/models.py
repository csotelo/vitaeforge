from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Lang(str, Enum):
    ES = "es"
    EN = "en"

class CertificationCategory(str, Enum):
    PROFESSIONAL = "professional"
    EXTRACURRICULAR = "extracurricular"

class ProjectCategory(str, Enum):
    OPEN_SOURCE = "open_source"
    ACTIVISM    = "activism"
    COMMUNITY   = "community"

class LocalizedString(BaseModel):
    es: str
    en: str

    def get(self, lang: Lang) -> str:
        return self.es if lang == Lang.ES else self.en

class Certification(BaseModel):
    name: LocalizedString
    issuer: str
    date: str
    credential_id: str
    credential_url: Optional[str] = None
    category: CertificationCategory = CertificationCategory.PROFESSIONAL

class Course(BaseModel):
    name: LocalizedString
    issuer: str
    date: str

class Project(BaseModel):
    name: LocalizedString
    url: Optional[str] = None
    category: ProjectCategory
    start_date: str
    end_date: str
    bullets: List[LocalizedString] = Field(default_factory=list)

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

class SkillTag(BaseModel):
    skill: str
    tags: List[str]

class Education(BaseModel):
    institution: str
    location: LocalizedString
    degree: LocalizedString
    start_date: str
    end_date: str

class Language(BaseModel):
    name: LocalizedString
    level: LocalizedString

class ThemeSection(BaseModel):
    key: str
    name: str
    optional: bool = True
    requires_profile: bool = False
    max_entries: Optional[int] = None
    max_bullets: Optional[int] = None

class ThemeConfig(BaseModel):
    theme_name: str
    sections: List[ThemeSection]
    design: Dict[str, Any]
    one_page: bool = False

class Profile(BaseModel):
    name: str
    title: LocalizedString
    summary: LocalizedString
    ats_keywords: List[str]
    skill_tags: List[str] = Field(default_factory=list)
    theme: str = "globant"

class CVData(BaseModel):
    name: str
    lastname: str
    email: str
    phone: str
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: LocalizedString
    experience: List[Experience]
    skills: List[SkillTag]
    education: List[Education]
    courses: List[Course]
    certifications: List[Certification]
    achievements: List[LocalizedString] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
