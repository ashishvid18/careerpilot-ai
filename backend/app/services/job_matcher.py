
import json
import re
from pathlib import Path

from app.models import ResumeProfile

JOBS_FILE = Path(__file__).resolve().parents[2] / "data" / "jobs.json"

REMOTE_TERMS = (
    "remote",
    "work from home",
    "work-from-home",
    "wfh",
)

# Normalize common title variations before comparing roles.
ROLE_ALIASES = {
    "sde": "software engineer",
    "software developer": "software engineer",
    "ml engineer": "machine learning engineer",
    "ai engineer": "artificial intelligence engineer",
    "data scientist": "data science",
    "frontend": "front end",
    "backend": "back end",
    "fullstack": "full stack",
    "react native developer": "mobile developer react native",
    "android developer": "mobile developer android",
    "ios developer": "mobile developer ios",
}

GENERIC_TITLE_WORDS = {
    "developer", "engineer", "intern", "senior", "junior",
    "associate", "lead", "staff", "principal", "graduate",
    "trainee", "the", "and", "for", "of",
}

# These are equivalent only for title matching, not strict filters.
TITLE_GROUPS = {
    "mobile": {
        "android", "ios", "mobile", "react native", "flutter"
    },
    "web_frontend": {
        "frontend", "front end", "react", "angular", "vue"
    },
    "web_backend": {
        "backend", "back end", "api", "server"
    },
    "machine_learning": {
        "machine learning", "ml", "artificial intelligence", "ai"
    },
    "data": {
        "data analyst", "data analytics", "data scientist",
        "data science", "business intelligence"
    },
}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value).strip()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", value.lower()))


def _normalize_title(value: str) -> str:
    title = re.sub(r"[^a-z0-9+#.\s-]", " ", value.lower())
    title = re.sub(r"[-_/]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    for alias, replacement in sorted(
        ROLE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        title = re.sub(
            rf"\b{re.escape(alias)}\b", replacement, title
        )

    return title


def _load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        raise RuntimeError(f"Job dataset not found: {JOBS_FILE}")

    try:
        with JOBS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not read the job dataset.") from exc

    if not isinstance(data, list):
        raise RuntimeError("The job dataset must contain a JSON list.")

    return [job for job in data if isinstance(job, dict)]


def _experience_range(value: str) -> tuple[float, float | None] | None:
    """
    Return (minimum years, maximum years).
    None means the listing does not provide a usable range.
    """
    text = value.lower().strip()

    if not text or any(
        phrase in text
        for phrase in ("not specified", "unknown", "not mentioned", "n/a")
    ):
        return None

    if any(
        phrase in text
        for phrase in (
            "fresher", "entry level", "no experience",
            "internship", "intern",
        )
    ):
        return (0.0, 1.0)

    # Examples: 2-4 years, 2 to 4 years, 3+ years.
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*"
        r"(?:\+|plus)?\s*(?:years?|yrs?)",
        text,
    )
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return (min(low, high), max(low, high))

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(\+|plus)?\s*(?:years?|yrs?)",
        text,
    )
    if match:
        low = float(match.group(1))
        if match.group(2):
            return (low, None)
        return (low, low)

    return None


def _experience_years(value: str) -> float | None:
    if not value:
        return None

    parsed = _experience_range(value)
    if parsed is None:
        return None

    # Candidate experience is treated as an approximate value.
    low, high = parsed
    return low if high is None else (low + high) / 2


def _job_skills(job: dict) -> set[str]:
    skills = job.get("skills", [])
    if not isinstance(skills, list):
        return set()

    return {
        _normalize_skill(str(skill))
        for skill in skills
        if str(skill).strip()
    }


def _normalize_skill(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "scikit learn": "scikit-learn",
        "sklearn": "scikit-learn",
        "node": "node.js",
        "reactjs": "react",
        "react.js": "react",
        "postgres": "postgresql",
        "ml": "machine learning",
        "ai/ml": "artificial intelligence",
    }
    return aliases.get(value, value)


def _title_relevance(designation: str, title: str) -> int:
    desired_title = _normalize_title(designation)
    job_title = _normalize_title(title)

    if not desired_title or not job_title:
        return 0

    if desired_title == job_title:
        return 35

    desired_tokens = _tokens(desired_title) - GENERIC_TITLE_WORDS
    job_tokens = _tokens(job_title) - GENERIC_TITLE_WORDS

    if not desired_tokens or not job_tokens:
        return 0

    overlap = len(desired_tokens & job_tokens) / len(desired_tokens)
    reverse_overlap = len(desired_tokens & job_tokens) / len(job_tokens)

    if overlap >= 0.8 and reverse_overlap >= 0.5:
        return 30
    if overlap >= 0.6:
        return 24
    if overlap >= 0.35:
        return 15

    # Related roles receive a small bonus, not an automatic strong match.
    for group in TITLE_GROUPS.values():
        desired_in_group = any(
            phrase in desired_title for phrase in group
        )
        job_in_group = any(phrase in job_title for phrase in group)

        if desired_in_group and job_in_group:
            return 10

    return 0


def _experience_score(
    candidate_years: float | None,
    requirement: str,
) -> tuple[int, str]:
    job_range = _experience_range(requirement)

    if candidate_years is None:
        return 0, "Candidate experience could not be confidently determined."

    if job_range is None:
        return 0, "The job's experience requirement is unspecified."

    minimum, maximum = job_range

    if candidate_years < minimum:
        gap = minimum - candidate_years

        if gap <= 1:
            return -5, "You may be slightly below the stated experience range."
        return -15, "The stated experience requirement exceeds your reported experience."

    if maximum is not None and candidate_years > maximum + 5:
        return 3, "You meet the minimum experience, though this role may be more junior."

    return 15, "Your reported experience fits the stated requirement."


def match_jobs(
    profile: ResumeProfile,
    limit: int = 10,
    keywords: str = "",
    location: str = "",
    remote_only: bool = False,
) -> dict:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    jobs = _load_jobs()

    profile_skills = {
        _normalize_skill(skill)
        for skill in profile.skills
        if skill and skill.strip()
    }

    designation = profile.designation or ""
    candidate_years = _experience_years(profile.experience or "")
    keyword_tokens = _tokens(keywords)
    location_query = location.strip().lower()

    ranked = []

    for job in jobs:
        title = _text(job.get("title"))
        company = _text(job.get("company"))
        job_location = _text(job.get("location"))
        description = _text(job.get("description"))
        experience_required = _text(job.get("experience_required"))
        raw_skills = job.get("skills", [])
        skills = raw_skills if isinstance(raw_skills, list) else []

        job_skills = _job_skills(job)

        combined_text = " ".join(
            [title, company, job_location, description, experience_required]
            + [str(skill) for skill in skills]
        )
        combined_tokens = _tokens(combined_text)
        combined_lower = combined_text.lower()

        # Keep explicit user filters separate from relevance scoring.
        if keyword_tokens and not keyword_tokens.issubset(combined_tokens):
            continue

        if location_query and location_query not in job_location.lower():
            continue

        if remote_only and not any(
            term in combined_lower for term in REMOTE_TERMS
        ):
            continue

        matched_skills = sorted(profile_skills & job_skills)
        reasons = []

        # Score components: title 35, skills 45, experience 15,
        # and evidence in the job description 5.
        title_score = _title_relevance(designation, title)
        score = title_score

        if title_score >= 30:
            reasons.append("Strong job-title alignment.")
        elif title_score >= 15:
            reasons.append("Partial job-title alignment.")
        elif title_score > 0:
            reasons.append("Some overlap with a related role.")
        elif designation:
            reasons.append("The job title does not strongly match your target role.")

        if profile_skills:
            skill_coverage = len(matched_skills) / len(profile_skills)
            skill_score = round(45 * skill_coverage)
            score += skill_score

            if matched_skills:
                reasons.append(
                    "Matching listed skills: " + ", ".join(matched_skills[:8])
                )
            else:
                reasons.append("No exact overlap between the listed skill sets.")
        else:
            skill_score = 0
            reasons.append("Add or verify resume skills for more reliable ranking.")

        experience_points, experience_reason = _experience_score(
            candidate_years, experience_required
        )
        score += experience_points
        reasons.append(experience_reason)

        # Description evidence adds only a small bonus. Avoid counting
        # generic words such as "work", "team", or "experience".
        important_profile_terms = (
            profile_skills | (_tokens(designation) - GENERIC_TITLE_WORDS)
        )
        description_tokens = _tokens(description)
        description_overlap = important_profile_terms & description_tokens

        if important_profile_terms:
            description_score = round(
                5 * min(1.0, len(description_overlap) / 3)
            )
            score += description_score

            if description_overlap:
                reasons.append("Relevant skills or role terms appear in the description.")
        else:
            description_score = 0

        
        # Penalize clearly unrelated job titles.
        desired_title = _normalize_title(designation)
        actual_title = _normalize_title(title)

        desired_tokens = _tokens(desired_title) - GENERIC_TITLE_WORDS
        actual_tokens = _tokens(actual_title) - GENERIC_TITLE_WORDS

        title_overlap = (
            len(desired_tokens & actual_tokens) / len(desired_tokens)
            if desired_tokens
            else 0.0
        )

        if designation and title_score == 0:
            score -= 15
            reasons.append(
                "Penalty applied because the job title does not closely match your target role."
            )
        elif title_overlap < 0.25 and title_score < 15:
            score -= 8
            reasons.append(
                "The job title has limited overlap with your target role."
            )

        # Keep the score within 0–100.
        score = max(0, min(100, score))

        ranked.append({
            "job_id": _text(job.get("job_id")),
            "title": title,
            "company": company,
            "location": job_location,
            "experience_required": experience_required or "Not specified",
            "skills": skills,
            "description": description,
            "source": _text(job.get("source")),
            "source_url": _text(job.get("source_url")),
            "match_score": score,
            "match_reasons": reasons,
            "_title_score": title_score,
            "_skill_score": skill_score,
            "_experience_score": experience_points,
            "_description_score": description_score,
            "_matched_skill_count": len(matched_skills),
        })

    # Tie-break on title fit and skill overlap instead of dataset order.
    ranked.sort(
        key=lambda item: (
            item["match_score"],
            item["_title_score"],
            item["_skill_score"],
            item["_matched_skill_count"],
        ),
        reverse=True,
    )

    for job in ranked:
        job.pop("_title_score", None)
        job.pop("_skill_score", None)
        job.pop("_experience_score", None)
        job.pop("_description_score", None)
        job.pop("_matched_skill_count", None)

    return {
        "total": len(ranked),
        "results": ranked[:limit],
    }
