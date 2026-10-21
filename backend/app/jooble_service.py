
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("careerpilot.jobs")

JOBS_FILE = Path(__file__).resolve().parents[1] / "data" / "jobs.json"
PAGE_SIZE = 20


def load_jobs() -> list[dict]:
    """Load scraped jobs from the local JSON dataset."""
    if not JOBS_FILE.exists():
        raise RuntimeError(
            f"Job dataset not found: {JOBS_FILE}"
        )

    try:
        with JOBS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        logger.exception("Could not load the job dataset")
        raise RuntimeError(
            "The local job dataset could not be read."
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError(
            "The job dataset must contain a JSON list."
        )

    return [job for job in data if isinstance(job, dict)]


def tokenize(value: str) -> set[str]:
    """Convert text into searchable words."""
    return set(re.findall(r"[a-zA-Z0-9+#.]+", value.lower()))


def job_text(job: dict) -> str:
    """Combine searchable job fields."""
    skills = job.get("skills", [])
    if isinstance(skills, list):
        skills_text = " ".join(str(skill) for skill in skills)
    else:
        skills_text = str(skills or "")

    return " ".join(
        str(value or "")
        for value in [
            job.get("title"),
            job.get("company"),
            job.get("description"),
            job.get("experience_required"),
            job.get("location"),
            skills_text,
        ]
    )


def normalize_job(job: dict) -> dict:
    """Return the API response format expected by the frontend."""
    skills = job.get("skills", [])

    return {
        "id": str(job.get("job_id", "")),
        "title": job.get("title") or "Untitled role",
        "company": job.get("company") or "Not specified",
        "location": job.get("location") or "Not specified",
        "description": job.get("description") or "",
        "url": job.get("source_url") or "",
        "salary": job.get("salary") or "",
        "source": job.get("source") or "Local dataset",
        "updated": job.get("date_posted") or "",
        "experience_required": (
            job.get("experience_required") or "Not specified"
        ),
        "skills": skills if isinstance(skills, list) else [],
    }


def search_jobs(
    keywords: str,
    location: str = "Bengaluru",
    page: int = 1,
) -> dict:
    """Search the local dataset and return paginated job results."""
    if not keywords.strip():
        raise ValueError("Keywords are required.")

    if page < 1:
        raise ValueError("Page must be 1 or greater.")

    all_jobs = load_jobs()
    keyword_tokens = tokenize(keywords)
    location_query = location.strip().lower()

    matches = []

    for job in all_jobs:
        title = str(job.get("title") or "")
        company = str(job.get("company") or "")
        job_location = str(job.get("location") or "")
        searchable_text = job_text(job)
        searchable_tokens = tokenize(searchable_text)

        # Require at least one keyword match.
        overlap = keyword_tokens & searchable_tokens
        if not overlap:
            continue

        # Prefer title matches over matches elsewhere.
        title_tokens = tokenize(title)
        score = len(overlap) + 3 * len(keyword_tokens & title_tokens)

        # Apply the requested location when it has matches.
        location_matches = (
            not location_query
            or location_query in job_location.lower()
            or location_query == "india"
        )

        matches.append(
            (score, location_matches, job)
        )

    # Prefer jobs matching both keywords and location.
    if location_query and location_query != "india":
        local_matches = [
            item for item in matches if item[1]
        ]
        if local_matches:
            matches = local_matches

    matches.sort(
        key=lambda item: (
            item[0],
            bool(item[2].get("description")),
        ),
        reverse=True,
    )

    total = len(matches)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    return {
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "jobs": [
            normalize_job(job)
            for _, _, job in matches[start:end]
        ],
    }
