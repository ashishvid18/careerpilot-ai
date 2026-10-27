
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.models import (
    ApplicationItem,
    ApplicationStatusRequest,
    ApplyRequest,
    ChatRequest,
    ChatResponse,
    ResumeProfile,
)
from app.agents.orchestrator import OrchestratorAgent
from app.agents.resume_agent import ResumeAgent
from app.jooble_service import search_jobs
from app.database.store import (
    initialize_database,
    save_application,
    list_applications,
    update_application_status,
)
from app.services.job_matcher import match_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careerpilot")

app = FastAPI(
    title="CareerPilot AI API",
    version="0.3.0",
    description="Conversational AI Job Assistant API with Agent Orchestration",
)

# Allow CORS for development and deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = OrchestratorAgent()
resume_agent = ResumeAgent()


@app.on_event("startup")
def startup():
    initialize_database()
    logger.info("Database initialized successfully.")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "careerpilot-api",
        "version": "0.3.0",
        "agent": "OrchestratorAgent ready",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Orchestrator chat endpoint. Routes user messages to specialized agents:
    - ResumeAgent
    - JobAgent (matching, filtering, recommendations)
    - ApplicationAgent (apply, deduplicate, status)
    """
    started = time.monotonic()
    logger.info("Chat request received: %s (session: %s)", request.message[:60], request.session_id)
    try:
        response = orchestrator.handle_message(request)
        logger.info("Chat processed by Orchestrator in %.2fs (intent=%s)", time.monotonic() - started, response.intent)
        return response
    except Exception as exc:
        logger.exception("Orchestrator chat handling failed")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your message: {exc}",
        )


@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    """Upload and parse a PDF or DOCX resume using ResumeAgent with heuristic fallback."""
    started = time.monotonic()
    filename = file.filename or "resume"
    content = await file.read()

    try:
        profile, char_count = resume_agent.parse_from_bytes(filename, content)
        logger.info("Resume parsed in %.2fs (chars=%d)", time.monotonic() - started, char_count)
        return {
            "profile": profile.model_dump(),
            "text_characters": char_count,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Resume parsing failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail=f"Resume parsing failed: {exc}",
        )


@app.get("/api/jobs/search")
def jobs_search(
    keywords: str = "Python Developer",
    location: str = "Bengaluru",
    page: int = Query(default=1, ge=1),
):
    if not keywords.strip():
        raise HTTPException(status_code=400, detail="Keywords are required.")
    if not location.strip():
        raise HTTPException(status_code=400, detail="Location is required.")

    try:
        return search_jobs(
            keywords=keywords.strip(),
            location=location.strip(),
            page=page,
        )
    except Exception as exc:
        logger.exception("Job search failed")
        raise HTTPException(status_code=502, detail=f"Job search failed: {exc}")


@app.post("/api/jobs/match")
def jobs_match(
    profile: ResumeProfile,
    keywords: str = "",
    location: str = "",
    remote_only: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
):
    try:
        return match_jobs(
            profile=profile,
            limit=limit,
            keywords=keywords.strip() if keywords else "",
            location=location.strip() if location else "",
            remote_only=remote_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Job matching failed")
        raise HTTPException(status_code=500, detail=f"Job matching failed: {exc}")


@app.post("/api/applications")
def create_application(request: ApplyRequest):
    """Save an application record, preventing duplicate entries."""
    try:
        from app.agents.application_agent import _load_job_lookup
        lookup = _load_job_lookup()

        if request.job_id not in lookup:
            raise HTTPException(
                status_code=404,
                detail=f"Job ID '{request.job_id}' was not found in the job dataset.",
            )

        job_meta = lookup[request.job_id]
        result = orchestrator.application_agent.apply(
            session_id=request.session_id,
            job_data=job_meta,
            status=request.status or "submitted",
        )
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Create application failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/applications")
def get_applications(session_id: str = "local-session"):
    """Retrieve all applications for a session enriched with job details."""
    try:
        apps = orchestrator.application_agent.list_applications_enriched(session_id)
        return {
            "total": len(apps),
            "applications": apps,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.patch("/api/applications/status")
def change_application_status(request: ApplicationStatusRequest):
    """Update application status."""
    try:
        application = update_application_status(
            session_id=request.session_id,
            job_id=request.job_id,
            status=request.status,
        )
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Application record was not found.",
            )
        return {
            "message": "Application status updated.",
            "application": application,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# Mount compiled frontend static build if present
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    logger.info("Serving compiled frontend from: %s", frontend_dist)
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        # Route non-API 404s back to index.html for SPA client-side routing
        if not request.url.path.startswith("/api"):
            return FileResponse(frontend_dist / "index.html")
        raise HTTPException(status_code=404, detail="Not Found")

