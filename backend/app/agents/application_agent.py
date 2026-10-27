import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.database.store import (
    list_applications,
    save_application,
    update_application_status,
)

logger = logging.getLogger("careerpilot.agents.application")

JOBS_FILE = Path(__file__).resolve().parents[2] / "data" / "jobs.json"


def _load_job_lookup() -> Dict[str, Dict[str, Any]]:
    """Load jobs mapped by job_id for quick lookup."""
    if not JOBS_FILE.exists():
        return {}
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {str(j.get("job_id")): j for j in data if isinstance(j, dict)}
    except Exception as exc:
        logger.warning("Could not build job lookup table: %s", exc)
        return {}


class ApplicationAgent:
    """Agent responsible for applying to jobs, preventing duplicates, and tracking application status."""

    def __init__(self):
        self._jobs_lookup: Optional[Dict[str, Dict[str, Any]]] = None

    def _get_lookup(self) -> Dict[str, Dict[str, Any]]:
        if self._jobs_lookup is None:
            self._jobs_lookup = _load_job_lookup()
        return self._jobs_lookup

    def resolve_job(
        self,
        query: str,
        recent_jobs: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Resolve a job from conversational query.
        Supports:
        - Index based: 'apply to job 3', 'apply to #2', 'job 1', 'the third one'
        - ID based: 'in-df59069aee154a4d'
        - Title based: 'apply to frontend engineer'
        """
        lookup = self._get_lookup()
        query_clean = query.strip()
        query_lower = query_clean.lower()

        # 1. Direct Job ID match
        for job_id, job in lookup.items():
            if job_id.lower() in query_lower:
                return job, None

        # 2. Numbered index in recent recommendations (e.g., 'job 3', 'job #2', 'apply to 1')
        recent = recent_jobs or []
        index_patterns = [
            r"\b(?:job|role|position|number|#)\s*([0-9]{1,2})\b",
            r"\bapply\s+to\s+([0-9]{1,2})\b",
            r"\bapply\s+([0-9]{1,2})\b",
            r"\b#([0-9]{1,2})\b",
        ]

        ordinal_words = {
            "first": 1,
            "1st": 1,
            "second": 2,
            "2nd": 2,
            "third": 3,
            "3rd": 3,
            "fourth": 4,
            "4th": 4,
            "fifth": 5,
            "5th": 5,
        }
        for word, idx in ordinal_words.items():
            if re.search(rf"\b{word}\b", query_lower):
                if 1 <= idx <= len(recent):
                    return recent[idx - 1], None
                return None, f"You asked for the {word} job, but only {len(recent)} jobs were listed."

        for pattern in index_patterns:
            match = re.search(pattern, query_lower)
            if match:
                idx = int(match.group(1))
                if 1 <= idx <= len(recent):
                    return recent[idx - 1], None
                elif recent:
                    return (
                        None,
                        f"Job #{idx} is not in your current recommendations list (we showed 1 to {len(recent)}). "
                        "Please pick a valid job number or ask for more recommendations.",
                    )
                else:
                    return (
                        None,
                        "I don't have an active list of job recommendations in our chat yet. "
                        "Please ask me to recommend jobs or upload your resume first!",
                    )

        # 3. Match by title substring in recent recommendations
        if recent:
            for job in recent:
                title = job.get("title", "").lower()
                if title and title in query_lower:
                    return job, None

        # 4. Fallback: single number only query e.g. '3' or '2'
        single_num = re.match(r"^\s*([0-9]{1,2})\s*$", query_clean)
        if single_num and recent:
            idx = int(single_num.group(1))
            if 1 <= idx <= len(recent):
                return recent[idx - 1], None

        return (
            None,
            "I couldn't identify which job you'd like to apply to. "
            "Please specify a job number (e.g. *'apply to job 1'*) or a specific Job ID.",
        )

    def apply(
        self,
        session_id: str,
        job_data: Dict[str, Any],
        status: str = "submitted",
    ) -> Dict[str, Any]:
        """Apply to a job, recording it in the SQLite database and avoiding duplicates."""
        job_id = str(job_data.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("Invalid job data: missing job_id.")

        record = save_application(
            session_id=session_id,
            job_id=job_id,
            status=status,
        )

        title = job_data.get("title", "Job Role")
        company = job_data.get("company", "Company")
        location = job_data.get("location", "")
        source_url = job_data.get("source_url", "")

        is_new = record.get("created", False)
        applied_at = record.get("applied_at", "today")

        if is_new:
            message = (
                f"🎉 **Application Submitted Successfully!**\n\n"
                f"- **Role:** {title}\n"
                f"- **Company:** {company}\n"
                f"- **Location:** {location}\n"
                f"- **Job ID:** `{job_id}`\n"
                f"- **Status:** `Submitted`\n"
                f"- **Date:** {applied_at}\n\n"
                f"Your application has been safely recorded in your **Application Tracker**. "
                f"You can say *'Show my applied jobs'* anytime to check all your applications!"
            )
        else:
            current_status = record.get("status", "submitted").replace("_", " ").title()
            message = (
                f"ℹ️ **Already Applied:**\n\n"
                f"You previously applied to **{title}** at **{company}** on {applied_at}. "
                f"Current status: `{current_status}`. Duplicate submission was prevented."
            )

        return {
            "created": is_new,
            "record": record,
            "message": message,
            "job": job_data,
        }

    def list_applications_enriched(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve applications for this session and enrich with title and company."""
        lookup = self._get_lookup()
        records = list_applications(session_id)
        enriched = []
        for rec in records:
            job_id = rec.get("job_id")
            meta = lookup.get(job_id, {})
            enriched.append({
                "id": rec.get("id"),
                "session_id": rec.get("session_id"),
                "job_id": job_id,
                "applied_at": rec.get("applied_at"),
                "status": rec.get("status"),
                "title": meta.get("title", "Saved Job"),
                "company": meta.get("company", "Company"),
                "location": meta.get("location", ""),
                "source_url": meta.get("source_url", ""),
            })
        return enriched

    def format_status_markdown(self, session_id: str) -> str:
        """Format a list of all applied jobs into a clean conversational markdown response."""
        applications = self.list_applications_enriched(session_id)
        if not applications:
            return (
                "You haven't applied to any jobs yet! "
                "Upload your resume or ask me for matching jobs, then tell me *'Apply to job 1'* to submit an application."
            )

        lines = [
            f"### 📋 Your Applied Jobs ({len(applications)} total)\n",
            "Here is the current status of all your recorded applications:\n",
        ]

        for idx, app in enumerate(applications, start=1):
            title = app.get("title", "Job")
            company = app.get("company", "Company")
            location = app.get("location", "")
            job_id = app.get("job_id", "")
            status = str(app.get("status", "submitted")).replace("_", " ").title()
            date = app.get("applied_at", "")
            link = app.get("source_url", "")

            lines.append(f"**{idx}. {title}** @ {company}")
            lines.append(f"- **Job ID:** `{job_id}` | **Status:** `{status}` | **Applied:** {date}")
            if location:
                lines.append(f"- **Location:** {location}")
            if link:
                lines.append(f"- [View Original Posting ↗]({link})")
            lines.append("")

        lines.append("> Use the sidebar **Application Tracker** to change application statuses as you hear back from employers!")
        return "\n".join(lines)

