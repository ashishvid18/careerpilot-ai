
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REQUIRED_FIELDS = (
    "job_id",
    "title",
    "company",
    "location",
    "experience_required",
    "skills",
    "description",
    "source_url",
)

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "referrer",
}


def normalize_text(value) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_url(url: str) -> str:
    url = normalize_text(url)

    if not url:
        return ""

    try:
        parts = urlsplit(url)

        # Remove tracking parameters, but preserve meaningful parameters
        # such as Indeed's "jk", which identifies an individual job.
        query_params = []

        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        ):
            key_lower = key.lower()

            if key_lower.startswith("utm_"):
                continue

            if key_lower in TRACKING_PARAMS:
                continue

            query_params.append((key, value))

        # Sort parameters to make equivalent URLs consistent.
        query_params.sort(key=lambda item: (item[0].lower(), item[1]))

        normalized_netloc = parts.netloc.lower()
        normalized_path = parts.path.rstrip("/") or "/"
        normalized_query = urlencode(query_params, doseq=True)

        return urlunsplit(
            (
                parts.scheme.lower(),
                normalized_netloc,
                normalized_path,
                normalized_query,
                "",
            )
        )

    except ValueError:
        return url


def normalize_job(job: dict) -> dict:
    normalized = dict(job)

    text_fields = (
        "job_id",
        "title",
        "company",
        "location",
        "experience_required",
        "description",
        "source",
    )

    for field in text_fields:
        normalized[field] = normalize_text(normalized.get(field))

    skills = normalized.get("skills", [])

    if isinstance(skills, str):
        skills = re.split(r"[,;|]", skills)

    if not isinstance(skills, list):
        skills = []

    normalized["skills"] = sorted(
        {
            normalize_text(skill)
            for skill in skills
            if normalize_text(skill)
        }
    )

    normalized["source_url"] = normalize_url(
        normalized.get("source_url", "")
    )

    return normalized


def validate_job(job: dict) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        value = job.get(field)

        if field == "skills":
            if not isinstance(value, list):
                errors.append("skills must be a list")
        elif not value:
            errors.append(f"{field} is missing")

    return errors


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    unique_jobs = []
    seen = set()

    for raw_job in jobs:
        job = normalize_job(raw_job)

        if validate_job(job):
            continue

        source_url = job["source_url"]

        if source_url:
            identity = source_url.lower()
        else:
            identity = (
                f'{job["source"].lower()}:{job["job_id"]}'
            )

        if identity in seen:
            continue

        seen.add(identity)
        unique_jobs.append(job)

    return unique_jobs
