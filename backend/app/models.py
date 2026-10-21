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

class ChatRequest(BaseModel):
    message: str
    session_id: str = "local-session"
    resume_profile: ResumeProfile | None = None
    
class ChatResponse(BaseModel):
    reply: str
    intent: str = "general"
