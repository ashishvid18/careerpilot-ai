
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse, ResumeProfile
from app.services.resume_parser import extract_resume_text
from app.services.gemini_service import (
    parse_resume_with_gemini,
    reply_to_message,
)
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
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "careerpilot-api",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        reply = reply_to_message(
            message=request.message,
            resume_profile=request.resume_profile,
        )
        return ChatResponse(reply=reply)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Chat failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini request failed. Check API configuration "
                "and try again."
            ),
        )


@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    filename = file.filename or "resume"

    if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF or DOCX file.",
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Resume must be smaller than 10 MB.",
        )

    try:
        text = extract_resume_text(filename, content)

        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text was found in the resume.",
            )

        profile = parse_resume_with_gemini(text)

        return {
            "profile": profile.model_dump(),
            "text_characters": len(text),
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Resume parsing failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Resume parsing failed. Check Gemini configuration "
                "and try again."
            ),
        )


@app.get("/api/jobs/search")
def jobs_search(
    keywords: str = "Python Developer",
    location: str = "Bengaluru",
    page: int = Query(default=1, ge=1),
):
    if not keywords.strip():
        raise HTTPException(
            status_code=400,
            detail="Keywords are required.",
        )

    if not location.strip():
        raise HTTPException(
            status_code=400,
            detail="Location is required.",
        )

    try:
        return search_jobs(
            keywords=keywords.strip(),
            location=location.strip(),
            page=page,
        )

    except RuntimeError as exc:
        logger.exception("Job search failed")
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Job search failed")
        raise HTTPException(
            status_code=502,
            detail="Job search failed. Check the backend logs.",
        )


@app.post("/api/jobs/match")
def jobs_match(
    profile: ResumeProfile,
    keywords: str = "",
    location: str = "",
    remote_only: bool = False,
    limit: int = Query(default=10, ge=1, le=50),
):
    if keywords and not keywords.strip():
        keywords = ""

    if location and not location.strip():
        location = ""

    try:
        return match_jobs(
            profile=profile,
            limit=limit,
            keywords=keywords.strip(),
            location=location.strip(),
            remote_only=remote_only,
        )

    except RuntimeError as exc:
        logger.exception("Job matching failed")
        raise HTTPException(
            status_code=500,
            detail="Job matching failed. Check the backend logs.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Unexpected job matching failure")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during job matching.",
        )

    
from pydantic import BaseModel


class ApplyRequest(BaseModel):
    session_id: str = "local-session"
    job_id: str


class ApplicationStatusRequest(BaseModel):
    session_id: str = "local-session"
    job_id: str
    status: str


@app.post("/api/applications")
def create_application(request: ApplyRequest):
    try:
        # Verify that the requested job exists in the local dataset.
        from app.jooble_service import load_jobs

        jobs = load_jobs()
        valid_ids = {
            str(job.get("job_id", ""))
            for job in jobs
        }

        if request.job_id not in valid_ids:
            raise HTTPException(
                status_code=404,
                detail="Job ID was not found in the job dataset.",
            )

        application = save_application(
            session_id=request.session_id,
            job_id=request.job_id,
            status="saved_demo",
        )

        return {
            "message": (
                "Application record saved."
                if application["created"]
                else "This job is already saved in your applications."
            ),
            "application": application,
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/applications")
def get_applications(session_id: str = "local-session"):
    try:
        applications = list_applications(session_id)
        return {
            "total": len(applications),
            "applications": applications,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/applications/status")
def change_application_status(request: ApplicationStatusRequest):
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

