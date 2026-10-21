
import json
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

DATA_FILE = Path(__file__).parent / "data" / "jobs.json"

REQUIRED_FIELDS = [
    "job_id",
    "title",
    "company",
    "location",
    "experience_required",
    "skills",
    "description",
    "source_url",
]


def main():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        jobs = json.load(file)

    if not isinstance(jobs, list):
        raise ValueError("Expected jobs.json to contain a list.")

    print(f"Total records: {len(jobs)}")

    ids = [
        str(job.get("job_id", "")).strip()
        for job in jobs
    ]
    nonempty_ids = [job_id for job_id in ids if job_id]

    print(f"Unique non-empty job IDs: {len(set(nonempty_ids))}")
    print(f"Missing job IDs: {len(jobs) - len(nonempty_ids)}")
    print(f"Duplicate job IDs: {len(nonempty_ids) - len(set(nonempty_ids))}")

    print("\nRequired-field validation:")
    for field in REQUIRED_FIELDS:
        missing = sum(
            1 for job in jobs
            if field not in job
            or job[field] is None
            or job[field] == ""
            or job[field] == []
        )
        print(f"{field}: {missing} missing")

    missing_experience = sum(
        1 for job in jobs
        if str(job.get("experience_required", "")).strip().lower()
        in {"", "not specified", "unknown", "n/a"}
    )
    missing_skills = sum(
        1 for job in jobs
        if not job.get("skills")
    )

    valid_urls = sum(
        1 for job in jobs
        if urlparse(str(job.get("source_url", ""))).scheme in {"http", "https"}
        and urlparse(str(job.get("source_url", ""))).netloc
    )

    sources = Counter(
        str(job.get("source", "unknown")).lower()
        for job in jobs
    )

    print(f"\nExperience not specified: {missing_experience}")
    print(f"Jobs without skills: {missing_skills}")
    print(f"HTTP/HTTPS source URLs: {valid_urls}/{len(jobs)}")
    print(f"Sources: {dict(sources)}")


if __name__ == "__main__":
    main()
