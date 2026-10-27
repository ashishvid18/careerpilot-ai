import logging
from pathlib import Path
from typing import Tuple

from app.models import ResumeProfile
from app.services.resume_parser import extract_resume_text
from app.services.gemini_service import parse_resume_with_gemini
from app.services.heuristic_parser import parse_resume_heuristically

logger = logging.getLogger("careerpilot.agents.resume")


class ResumeAgent:
    """Agent responsible for resume reading, validation, and candidate profile extraction."""

    def parse_from_bytes(self, filename: str, content: bytes) -> Tuple[ResumeProfile, int]:
        """Extract text from file content and extract candidate profile details."""
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx"}:
            raise ValueError("Unsupported format. Please upload a PDF or DOCX resume.")

        if len(content) > 10 * 1024 * 1024:
            raise ValueError("Resume file exceeds 10 MB limit.")

        text = extract_resume_text(filename, content)
        if not text or len(text.strip()) < 30:
            raise ValueError(
                "Could not extract sufficient text from this resume. "
                "Please ensure the PDF or DOCX is not an image-only scan."
            )

        try:
            profile = parse_resume_with_gemini(text)
        except Exception as exc:
            logger.warning("Gemini parsing failed, using heuristic extraction: %s", exc)
            profile = parse_resume_heuristically(text)

        return profile, len(text)

    def parse_from_text(self, text: str) -> ResumeProfile:
        """Parse resume directly from plain text."""
        if not text or len(text.strip()) < 30:
            raise ValueError("Text provided is too short for resume analysis.")

        try:
            return parse_resume_with_gemini(text)
        except Exception as exc:
            logger.warning("Gemini parsing failed, using heuristic extraction: %s", exc)
            return parse_resume_heuristically(text)

