
import pytest

from app.models import ResumeProfile
from app.services import job_matcher


@pytest.fixture
def sample_jobs(monkeypatch):
    jobs = [
        {
            "job_id": "android-1",
            "title": "Android Developer Intern",
            "company": "Mobile Apps Ltd",
            "location": "Bengaluru, India",
            "experience_required": "Fresher",
            "skills": ["Android", "Java", "Kotlin"],
            "description": "Develop Android mobile applications using Java and Kotlin.",
            "source": "test",
            "source_url": "https://example.com/android",
        },
        {
            "job_id": "data-1",
            "title": "Data Scientist",
            "company": "Data Labs",
            "location": "Bengaluru, India",
            "experience_required": "3+ years",
            "skills": ["Python", "SQL", "Machine Learning", "Pandas"],
            "description": "Build machine learning models and analyze data using Python and SQL.",
            "source": "test",
            "source_url": "https://example.com/data",
        },
        {
            "job_id": "senior-1",
            "title": "Senior Full Stack Engineer",
            "company": "Web Systems",
            "location": "Pune, India",
            "experience_required": "5+ years",
            "skills": ["React", "TypeScript", "Node.js"],
            "description": "Build full stack web applications.",
            "source": "test",
            "source_url": "https://example.com/fullstack",
        },
    ]

    monkeypatch.setattr(job_matcher, "_load_jobs", lambda: jobs)


def test_android_profile_ranks_android_role_first(sample_jobs):
    profile = ResumeProfile(
        designation="Android Developer Intern",
        skills=["Android", "Java", "Kotlin"],
        experience="0 years",
        education=[],
        projects=[],
    )

    result = job_matcher.match_jobs(profile, limit=3)

    assert result["total"] == 3
    assert result["results"][0]["job_id"] == "android-1"


def test_data_science_profile_ranks_data_role_first(sample_jobs):
    profile = ResumeProfile(
        designation="Senior Data Scientist",
        skills=["Python", "SQL", "Machine Learning", "Pandas"],
        experience="5 years",
        education=[],
        projects=[],
    )

    result = job_matcher.match_jobs(profile, limit=3)

    assert result["total"] == 3
    assert result["results"][0]["job_id"] == "data-1"


def test_location_filter(sample_jobs):
    profile = ResumeProfile(
        designation="Android Developer",
        skills=["Android"],
        experience="0 years",
        education=[],
        projects=[],
    )

    result = job_matcher.match_jobs(
        profile,
        limit=10,
        location="Pune",
    )

    assert result["total"] == 1
    assert result["results"][0]["location"] == "Pune, India"


def test_remote_filter_returns_no_false_matches(sample_jobs):
    profile = ResumeProfile(
        designation="Data Scientist",
        skills=["Python"],
        experience="3 years",
        education=[],
        projects=[],
    )

    result = job_matcher.match_jobs(
        profile,
        limit=10,
        remote_only=True,
    )

    assert result["total"] == 0


def test_result_has_frontend_fields(sample_jobs):
    profile = ResumeProfile(
        designation="Android Developer",
        skills=["Java"],
        experience="0 years",
        education=[],
        projects=[],
    )

    result = job_matcher.match_jobs(profile, limit=1)
    job = result["results"][0]

    required_fields = {
        "job_id",
        "title",
        "company",
        "location",
        "experience_required",
        "skills",
        "description",
        "source",
        "source_url",
        "match_score",
        "match_reasons",
    }

    assert required_fields.issubset(job.keys())
    assert 0 <= job["match_score"] <= 100
    assert isinstance(job["match_reasons"], list)
