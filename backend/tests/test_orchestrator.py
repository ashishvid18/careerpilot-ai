import pytest
from app.agents.orchestrator import OrchestratorAgent
from app.models import ChatRequest, ResumeProfile


@pytest.fixture
def sample_profile():
    return ResumeProfile(
        name="Test Candidate",
        email="candidate@example.com",
        phone="+91 9999999999",
        designation="Python Developer",
        skills=["Python", "FastAPI", "React", "Docker", "PostgreSQL"],
        experience="2 years",
        education=["B.Tech Computer Science"],
        projects=["Portfolio Website", "AI Chatbot"],
    )


def test_orchestrator_recommend_matching_jobs(sample_profile):
    orchestrator = OrchestratorAgent()
    req = ChatRequest(
        message="Find matching jobs for my profile",
        session_id="test-session-1",
        resume_profile=sample_profile,
    )
    res = orchestrator.handle_message(req)
    assert res.intent in ["recommend_jobs", "refine_jobs"]
    assert res.jobs is not None
    assert len(res.jobs) > 0
    # Match reasons should be included
    first_job = res.jobs[0]
    assert "match_score" in first_job
    assert len(first_job.get("match_reasons", [])) > 0
    assert "### Recommended Job Matches" in res.reply


def test_orchestrator_filter_remote_jobs(sample_profile):
    orchestrator = OrchestratorAgent()
    req = ChatRequest(
        message="show only remote roles",
        session_id="test-session-remote",
        resume_profile=sample_profile,
    )
    res = orchestrator.handle_message(req)
    assert res.jobs is not None
    assert len(res.jobs) > 0
    for job in res.jobs:
        combined = f"{job.get('title', '')} {job.get('location', '')} {job.get('description', '')}".lower()
        assert any(term in combined for term in ["remote", "work from home", "wfh"])


def test_orchestrator_filter_react_jobs(sample_profile):
    orchestrator = OrchestratorAgent()
    req = ChatRequest(
        message="show jobs needing React",
        session_id="test-session-react",
        resume_profile=sample_profile,
    )
    res = orchestrator.handle_message(req)
    assert res.jobs is not None
    assert len(res.jobs) > 0
    for job in res.jobs:
        skills = [str(s).lower() for s in job.get("skills", [])]
        desc = job.get("description", "").lower()
        assert "react" in skills or "react" in desc


def test_orchestrator_apply_flow_and_duplicate_prevention(sample_profile):
    orchestrator = OrchestratorAgent()
    # 1. First get some jobs
    match_req = ChatRequest(
        message="recommend jobs",
        session_id="test-session-apply",
        resume_profile=sample_profile,
    )
    match_res = orchestrator.handle_message(match_req)
    assert match_res.jobs is not None and len(match_res.jobs) >= 2

    # 2. Apply to job 1
    apply_req = ChatRequest(
        message="apply to job 1",
        session_id="test-session-apply",
        resume_profile=sample_profile,
        current_jobs=match_res.jobs,
    )
    apply_res = orchestrator.handle_message(apply_req)
    assert apply_res.intent == "apply_job"
    assert "Application Submitted Successfully" in apply_res.reply

    # 3. Apply to job 1 again -> Duplicate prevented
    duplicate_res = orchestrator.handle_message(apply_req)
    assert duplicate_res.intent == "apply_job"
    assert "Already Applied" in duplicate_res.reply or "Duplicate submission was prevented" in duplicate_res.reply

    # 4. Check status
    status_req = ChatRequest(
        message="show my applied jobs",
        session_id="test-session-apply",
    )
    status_res = orchestrator.handle_message(status_req)
    assert status_res.intent == "application_status"
    assert "Your Applied Jobs" in status_res.reply
    assert len(status_res.applications or []) >= 1


def test_orchestrator_invalid_job_reference():
    orchestrator = OrchestratorAgent()
    req = ChatRequest(
        message="apply to job 99",
        session_id="test-session-err",
        current_jobs=[{"job_id": "test-1", "title": "Dev"}],
    )
    res = orchestrator.handle_message(req)
    assert res.intent == "apply_job_error"
    assert "not in your current recommendations" in res.reply

