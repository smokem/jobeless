from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# --- Profile Models ---

class ContactInfo(BaseSchema):
    """Contact details nested inside personal_info."""
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    profile_picture: Optional[str] = None

class LocationInfo(BaseSchema):
    """Location details nested inside personal_info."""
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    remote_open: Optional[bool] = None
    relocation_open: Optional[bool] = None

class LanguageInfo(BaseSchema):
    """Language proficiency entry."""
    language: str
    proficiency: str
    code: Optional[str] = None
    certification: Optional[str] = None

class PersonalInfo(BaseSchema):
    """Matches actual profile.json personal_info structure."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    headline: Optional[str] = None
    location: Optional[LocationInfo] = None
    contact: Optional[ContactInfo] = None
    languages: Optional[List[LanguageInfo]] = None
    summary: Optional[str] = None

class WorkExperience(BaseSchema):
    id: Optional[str] = None
    company: str
    company_website: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_size: Optional[str] = None
    company_industry: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    location_type: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    achievements: Optional[List[str]] = None
    tech_stack: Optional[List[str]] = None

class Education(BaseSchema):
    id: Optional[str] = None
    institution: str
    degree: str
    field: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    graduation_year: Optional[int] = None
    status: Optional[str] = None
    grade: Optional[str] = None
    notable_projects: Optional[List[str]] = None
    notable_coursework: Optional[List[str]] = None
    extracurricular: Optional[str] = None
    location: Optional[str] = None

class Skill(BaseSchema):
    name: str
    level: str

class Project(BaseSchema):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    technologies: Optional[List[str]] = None
    tech_stack: Optional[List[str]] = None
    role: Optional[str] = None
    status: Optional[str] = None
    outcome: Optional[str] = None
    url: Optional[str] = None

class Certification(BaseSchema):
    id: Optional[str] = None
    name: str
    issuer: Optional[str] = None
    issued_date: Optional[str] = None
    type: Optional[str] = None

class VolunteerExperience(BaseSchema):
    id: Optional[str] = None
    organization: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    duration: Optional[str] = None
    responsibilities: Optional[List[str]] = None

class ProfileMeta(BaseSchema):
    """
    Top-level profile schema matching the actual profile.json structure.
    Uses flexible types for deeply nested sections like skills and cv_generation_hints.
    """
    meta: Optional[Dict[str, Any]] = None
    personal_info: PersonalInfo
    work_experience: Optional[List[WorkExperience]] = None
    education: Optional[List[Education]] = None
    skills: Optional[Dict[str, Any]] = None
    projects: Optional[List[Project]] = None
    certifications: Optional[List[Certification]] = None
    volunteer_experience: Optional[List[VolunteerExperience]] = None
    personality_and_work_style: Optional[Dict[str, Any]] = None
    preferences_and_goals: Optional[Dict[str, Any]] = None
    cv_generation_hints: Optional[Dict[str, Any]] = None

# --- Discovery & Research Models ---

class TargetCompany(BaseSchema):
    company_id: str
    company_name: str
    company_linkedin: HttpUrl
    company_website: Optional[HttpUrl] = None
    hr_name: Optional[str] = None
    hr_linkedin: Optional[HttpUrl] = None
    ceo_name: Optional[str] = None
    ceo_linkedin: Optional[HttpUrl] = None
    job_title: str
    job_url: HttpUrl
    apply_type: Literal["easy_apply", "email", "external"]
    location: str
    status: Literal["pending", "ignored", "applied"] = "pending"

class HiringPersona(BaseSchema):
    company_values: List[str]
    hr_communication_style: str
    what_they_look_for: List[str]
    red_flags_to_avoid: List[str]
    cultural_keywords: List[str]
    tone_preference: Literal["formal", "casual", "technical"]

class ApplicationMeta(BaseSchema):
    company_id: str
    company_info: TargetCompany
    persona: HiringPersona
    cv_score_achieved: float = 0.0
    status: str = "pending"

# --- Generation & GAN Models ---

class GANIteration(BaseSchema):
    iteration: int
    score: float
    notes: List[str]
    changes_made: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class CVData(BaseSchema):
    company_id: str
    cv_json: dict
    iterations: List[GANIteration]
    final_score: float

# --- History & Interview Models ---

class ApplicationHistory(BaseSchema):
    company_id: str
    company_name: str
    job_title: str
    date_sent: datetime
    apply_method: Literal["easy_apply", "email", "external"]
    cv_score_achieved: float
    status: Literal["sent", "opened", "replied", "interview", "rejected"]
    cv_path: str
    cl_path: str
    notes: Optional[str] = None

class InterviewMessage(BaseSchema):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class InterviewSession(BaseSchema):
    session_id: str
    company_id: str
    messages: List[InterviewMessage]
    performance_score: Optional[float] = None
    feedback: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
