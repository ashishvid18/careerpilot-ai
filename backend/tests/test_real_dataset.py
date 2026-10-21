
from app.models import ResumeProfile
from app.services.job_matcher import match_jobs


def test_real_dataset_returns_ranked_jobs():
    profile = ResumeProfile(
        designation="Android Developer Intern",
        skills=["Android", "Java", "Kotlin", "SQL"],
        experience="0 years",
        education=[],
        projects=[],
    )

    response = match_jobs(profile, limit=10)

    assert response["total"] > 0
    assert len(response["results"]) <= 10

    scores = [job["match_score"] for job in response["results"]]
    assert scores == sorted(scores, reverse=True)

    for job in response["results"]:
        assert job["job_id"]
        assert job["title"]
        assert 0 <= job["match_score"] <= 100
        assert isinstance(job["match_reasons"], list)

    print("\nTop 10 Android profile matches:")
    for job in response["results"]:
        print(
            f'{job["match_score"]:>3}/100 | '
            f'{job["title"]} | {job["company"]}'
        )
