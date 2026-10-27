from typing import Any
from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    designation: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: str | None = None
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class JobItem(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    experience_required: str = "Not specified"
    skills: list[str] = Field(default_factory=list)
    description: str = ""
    source: str = ""
    source_url: str = ""
    match_score: int = 0
    match_reasons: list[str] = Field(default_factory=list)


class ApplicationItem(BaseModel):
    id: int | None = None
    session_id: str = "local-session"
    job_id: str
    applied_at: str = ""
    status: str = "submitted"
    title: str = ""
    company: str = ""
    location: str = ""
    source_url: str = ""


class ChatRequest(BaseModel):
    message: str
    session_id: str = "local-session"
    resume_profile: ResumeProfile | None = None
    current_jobs: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str = "general"
    jobs: list[dict[str, Any]] | None = None
    applications: list[dict[str, Any]] | None = None
    suggested_actions: list[str] = Field(default_factory=list)


class ApplyRequest(BaseModel):
    session_id: str = "local-session"
    job_id: str
    status: str = "submitted"


class ApplicationStatusRequest(BaseModel):
    session_id: str = "local-session"
    job_id: str
    status: str
