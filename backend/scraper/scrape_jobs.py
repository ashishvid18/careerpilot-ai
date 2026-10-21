
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd
from dotenv import load_dotenv
from jobspy import scrape_jobs

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from normalize_jobs import normalize_job, validate_job

load_dotenv(BACKEND_DIR / ".env")


TECH_ROLE_TERMS = (
    "software",
    "developer",
    "engineer",
    "programmer",
    "data analyst",
    "data scientist",
    "machine learning",
    "artificial intelligence",
    " ai ",
    "deep learning",
    "nlp",
    "computer vision",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "devops",
    "cloud engineer",
    "qa engineer",
    "test engineer",
    "automation engineer",
    "database administrator",
    "database engineer",
    "business intelligence",
    "bi analyst",
    "cybersecurity",
    "cyber security",
    "network engineer",
    "it support",
    "technical support",
    "technical lead",
    "technology",
    "python",
    "java developer",
    "web developer",
    "mobile developer",
    "android developer",
    "ios developer",
    "data engineer",
    "analytics",
    "product analyst",
    "research scientist",
)

TRACKING_EXPERIENCE = re.compile(
    r"\b(?:"
    r"fresher|entry[- ]level|internship|intern|"
    r"junior|mid[- ]level|senior|lead"
    r")\b",
    re.IGNORECASE,
)

EXPERIENCE_PATTERNS = [
    re.compile(
        r"\b(\d{1,2})\s*(?:\+|plus)?\s*"
        r"(?:years?|yrs?)\s*(?:of\s*)?"
        r"(?:relevant\s*)?experience\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexperience\s*[:\-]\s*"
        r"(\d{1,2})\s*(?:\+|plus)?\s*"
        r"(?:years?|yrs?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*"
        r"(?:years?|yrs?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})"
        r"(?:-years?|-yrs?)\b",
        re.IGNORECASE,
    ),
]


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def csv_env(name, default):
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


def get_config():
    provider = os.getenv(
        "JOB_SCRAPER_PROVIDER", "both"
    ).strip().lower()

    if provider not in {"jobspy", "apify", "both"}:
        raise ValueError(
            "JOB_SCRAPER_PROVIDER must be jobspy, apify, or both."
        )

    results_wanted = env_int("JOBSPY_RESULTS_PER_SITE", 100)
    target = env_int("JOB_TARGET_COUNT", 1800)
    hours_old = env_int("JOBSPY_HOURS_OLD", 720)

    if results_wanted < 1:
        raise ValueError("JOBSPY_RESULTS_PER_SITE must be positive.")

    if target < 1:
        raise ValueError("JOB_TARGET_COUNT must be positive.")

    if hours_old < 0:
        raise ValueError("JOBSPY_HOURS_OLD cannot be negative.")

    job_type = os.getenv(
        "JOBSPY_JOB_TYPE", "fulltime"
    ).strip().lower()

    allowed_types = {
        "fulltime", "parttime", "internship", "contract",
        "temporary", "perdiem", "other", "volunteer",
    }

    if job_type not in allowed_types:
        raise ValueError(f"Unsupported JOBSPY_JOB_TYPE: {job_type}")

    try:
        apify_input = json.loads(
            os.getenv("APIFY_INPUT_JSON", "{}")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"APIFY_INPUT_JSON is invalid JSON: {exc}"
        ) from exc

    if not isinstance(apify_input, dict):
        raise ValueError("APIFY_INPUT_JSON must be a JSON object.")

    output_file = Path(
        os.getenv("JOB_OUTPUT_FILE", "data/jobs.json")
    )

    if not output_file.is_absolute():
        output_file = BACKEND_DIR / output_file

    return {
        "provider": provider,
        "sites": csv_env(
            "JOBSPY_SITES", "indeed,naukri,linkedin"
        ),
        "terms": csv_env(
            "JOBSPY_SEARCH_TERMS",
            "software engineer,python developer,"
            "data analyst,machine learning engineer",
        ),
        "location": os.getenv("JOBSPY_LOCATION", "India").strip(),
        "country_indeed": os.getenv(
            "JOBSPY_COUNTRY_INDEED", "India"
        ).strip(),
        "results_wanted": results_wanted,
        "hours_old": hours_old,
        "remote_only": env_bool("JOBSPY_REMOTE_ONLY", False),
        "job_type": job_type,
        "target": target,
        "apify_token": os.getenv("APIFY_API_TOKEN", "").strip(),
        "apify_actor_id": os.getenv("APIFY_ACTOR_ID", "").strip(),
        "apify_input": apify_input,
        "output_file": output_file,
    }


def first_value(record, *keys, default: Any = ""):
    """Return the first non-empty value among alternative field names."""
    for key in keys:
        value = record.get(key)

        if value is None:
            continue

        if isinstance(value, (dict, list)):
            if value:
                return value
            continue

        try:
            missing = pd.isna(value)
            if missing:
                continue
        except (TypeError, ValueError):
            pass

        if str(value).strip():
            return value

    return default


def as_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(as_text(item) for item in value if item is not None)

    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def extract_experience(record, description, title, source_url):
    """Extract experience only when the source gives usable evidence."""
    raw = first_value(
        record,
        "experience_required",
        "experienceRequired",
        "yearsExperience",
        "years_experience",
        "experience_range",
        "experienceRange",
        "experience_level",
        "experienceLevel",
        "seniorityLevel",
        "seniority_level",
        default="",
    )

    if raw:
        value = as_text(raw)
        if value.lower() not in {"nan", "none", "null"}:
            return value

    # Search description and title for explicit experience requirements.
    # Limit the text inspected to avoid matching unrelated long text.
    text = f"{title}\n{description[:5000]}"

    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)

        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} years"
            return f"{match.group(1)}+ years"

    # Some job URLs encode experience ranges, such as 5-to-10-years.
    url_path = urlsplit(source_url).path.lower()
    url_match = re.search(
        r"(\d{1,2})-to-(\d{1,2})-years?",
        url_path,
    )

    if url_match:
        return f"{url_match.group(1)}-{url_match.group(2)} years"

    return "Not specified"


def parse_skills(record, description):
    raw = first_value(
        record,
        "skills",
        "requiredSkills",
        "required_skills",
        "technologies",
        default=[],
    )

    if isinstance(raw, str):
        skills = [
            item.strip()
            for item in re.split(r"[,;|]", raw)
            if item.strip()
        ]
    elif isinstance(raw, list):
        skills = [as_text(item) for item in raw if as_text(item)]
    else:
        skills = []

    # Infer skills only from the actual description, never from the title.
    if not skills and description:
        common_terms = [
            "Python", "Java", "JavaScript", "TypeScript", "C++",
            "SQL", "React", "Node.js", "FastAPI", "Django",
            "Flask", "AWS", "Azure", "Docker", "Kubernetes",
            "Machine Learning", "Deep Learning", "TensorFlow",
            "PyTorch", "Pandas", "Excel", "Power BI", "Tableau",
            "HTML", "CSS", "Git", "PostgreSQL", "MongoDB",
        ]

        skills = [
            term for term in common_terms
            if re.search(
                rf"(?<!\w){re.escape(term)}(?!\w)",
                description,
                re.IGNORECASE,
            )
        ]

    return sorted(set(skills))


def is_relevant_role(title, description):
    """Keep likely technology, software, data, and AI-related roles."""
    text = f" {title.lower()} {description[:500].lower()} "

    return any(term in text for term in TECH_ROLE_TERMS)


def normalize_record(record, provider, fallback_id=""):
    """Map JobSpy or common Apify fields to the assessment schema."""
    if not isinstance(record, dict):
        return None

    title = as_text(first_value(
        record, "title", "jobTitle", "job_title", "position"
    ))

    company = as_text(first_value(
        record, "company", "companyName", "company_name", "employer"
    ))

    location = as_text(first_value(
        record,
        "location",
        "jobLocation",
        "formattedLocation",
        "formatted_location",
        "city",
    ))

    description = as_text(first_value(
        record,
        "description",
        "jobDescription",
        "job_description",
        "snippet",
        "text",
        "descriptionText",
    ))

    source_url = as_text(first_value(
        record,
        "job_url",
        "jobUrl",
        "url",
        "link",
        "job_link",
        "applyUrl",
        "apply_url",
    ))

    if not title or not company or not source_url:
        return None

    parsed_url = urlsplit(source_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return None

    # Filter unrelated roles instead of accepting every broad search result.
    if not is_relevant_role(title, description):
        return None

    job_id = as_text(first_value(
        record,
        "id",
        "job_id",
        "jobId",
        "jobID",
        "guid",
        default=fallback_id,
    ))

    if not job_id:
        job_id = source_url.rstrip("/").split("/")[-1]

    experience = extract_experience(
        record, description, title, source_url
    )

    skills = parse_skills(record, description)

    raw_remote = first_value(
        record, "is_remote", "isRemote", "remote", default=False
    )

    is_remote = (
        raw_remote is True
        or str(raw_remote).strip().lower() in {"true", "yes", "remote"}
    )

    source_name = as_text(first_value(
        record, "site", "source", "jobBoard", "job_board",
        default=provider,
    ))

    # Do not substitute the title for a missing description.
    description_quality = (
        "full_description" if len(description) >= 200
        else "short_description" if description
        else "missing"
    )

    job = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location or "Not specified",
        "experience_required": experience,
        "skills": skills,
        "description": description,
        "description_quality": description_quality,
        "source": source_name,
        "source_url": source_url,
        "is_remote": is_remote,
        "job_type": as_text(first_value(
            record,
            "job_type",
            "jobType",
            "employmentType",
            "employment_type",
        )) or "Not specified",
    }

    return normalize_job(job)


def collect_jobspy(config):
    records = []

    for term in config["terms"]:
        print(
            f"\n[JobSpy] Search: {term!r} "
            f"| Location: {config['location']}"
        )

        try:
            dataframe = scrape_jobs(
                site_name=config["sites"],
                search_term=term,
                location=config["location"],
                results_wanted=config["results_wanted"],
                hours_old=config["hours_old"],
                country_indeed=config["country_indeed"],
                job_type=config["job_type"],
                is_remote=config["remote_only"],
                description_format="markdown",
                fetch_description=True,
                verbose=1,
            )

            if dataframe is None or dataframe.empty:
                print(f"[JobSpy] No results returned for {term!r}.")
                continue

            rows = dataframe.to_dict(orient="records")
            print(f"[DEBUG] Search term: {term!r}; rows received: {len(rows)}")
            print(f"[DEBUG] First row fields: {list(rows[0].keys()) if rows else 'No rows'}")

            accepted = 0



            for index, row in enumerate(rows):
                job = normalize_record(
                    row,
                    "jobspy",
                    fallback_id=f"jobspy-{term}-{index}",
                )

                if job:
                    records.append(job)
                    accepted += 1

            print(
                f"[JobSpy] Received {len(rows)} rows; "
                f"{accepted} passed normalization and relevance checks."
            )

        except Exception as exc:
            print(
                f"[JobSpy] Search failed for {term!r}: "
                f"{type(exc).__name__}: {exc}"
            )

    return records


def collect_apify(config):
    actor_id = config["apify_actor_id"]
    token = config["apify_token"]

    if not actor_id:
        print(
            "\n[Apify] Skipped: APIFY_ACTOR_ID is blank. "
            "Configure an Actor to enable this provider."
        )
        return []

    if not token:
        print("\n[Apify] Skipped: APIFY_API_TOKEN is blank.")
        return []

    try:
        from apify_client import ApifyClient

        print(f"\n[Apify] Running Actor: {actor_id}")

        client = ApifyClient(token)
        run = client.actor(actor_id).call(
            run_input=config["apify_input"]
        )

        if not run:
            print("[Apify] Actor did not return a completed run.")
            return []

        dataset_id = (
            getattr(run, "default_dataset_id", None)
            or getattr(run, "defaultDatasetId", None)
        )

        if not dataset_id:
            print("[Apify] Run did not provide a dataset ID.")
            return []

        records = []

        for index, item in enumerate(
            client.dataset(dataset_id).iterate_items()
        ):
            job = normalize_record(
                item, "apify", fallback_id=f"apify-{index}"
            )

            if job:
                records.append(job)

        print(f"[Apify] {len(records)} records passed normalization.")
        return records

    except Exception as exc:
        print(
            f"[Apify] Collection failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return []


def validate_and_deduplicate(records):
    valid = []
    invalid_count = 0
    seen_urls = set()

    for job in records:
        if not isinstance(job, dict):
            invalid_count += 1
            continue

        normalized = normalize_job(job)

        # Description may be absent, but the field remains present and
        # description_quality makes the missing data explicit.
        errors = [
            error for error in validate_job(normalized)
            if error != "description is missing"
        ]

        source_url = normalized.get("source_url", "").strip().lower()
        parsed = urlsplit(source_url)

        if (
            errors
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
        ):
            invalid_count += 1
            continue

        if source_url in seen_urls:
            continue

        seen_urls.add(source_url)
        valid.append(normalized)

    return valid, invalid_count


def write_json(output_file, records):
    """Write atomically so an interrupted run won't corrupt jobs.json."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = output_file.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    temp_file.replace(output_file)


def main():
    config = get_config()
    collected = []

    if config["provider"] in {"jobspy", "both"}:
        collected.extend(collect_jobspy(config))

    if config["provider"] in {"apify", "both"}:
        collected.extend(collect_apify(config))

    unique_jobs, invalid_count = validate_and_deduplicate(collected)

    unique_jobs.sort(key=lambda job: (
        job.get("source", "").lower(),
        job.get("title", "").lower(),
        job.get("company", "").lower(),
    ))

    if len(unique_jobs) > config["target"]:
        unique_jobs = unique_jobs[:config["target"]]

    write_json(config["output_file"], unique_jobs)

    source_counts = Counter(
        job.get("source", "Unknown") for job in unique_jobs
    )
    description_counts = Counter(
        job.get("description_quality", "unknown")
        for job in unique_jobs
    )
    missing_experience = sum(
        job.get("experience_required") == "Not specified"
        for job in unique_jobs
    )
    missing_skills = sum(
        not job.get("skills") for job in unique_jobs
    )

    print("\n========== SCRAPE REPORT ==========")
    print(f"Provider setting: {config['provider']}")
    print(f"Raw normalized records: {len(collected)}")
    print(f"Invalid records skipped: {invalid_count}")
    print(f"Unique jobs saved: {len(unique_jobs)}")
    print(f"Target: {config['target']}")
    print(f"Output: {config['output_file']}")

    print("\nJobs by source:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    print("\nDescription quality:")
    for quality, count in sorted(description_counts.items()):
        print(f"  {quality}: {count}")

    print(f"\nJobs with unspecified experience: {missing_experience}")
    print(f"Jobs with no extracted skills: {missing_skills}")

    if len(unique_jobs) < config["target"]:
        print(
            "\nTarget not reached. No jobs were fabricated. "
            "Review source coverage and search configuration."
        )
    else:
        print("\nTarget reached.")

    print("===================================")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"Configuration or file error: {exc}")
        raise SystemExit(1)
