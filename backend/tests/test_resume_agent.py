import pytest
from app.agents.resume_agent import ResumeAgent
from app.services.heuristic_parser import parse_resume_heuristically
from app.models import ResumeProfile


SAMPLE_RESUME = """
Ashish Vidyarthi
ashish.vid@example.com
+91 9876543210
Bengaluru, India

Professional Summary:
Passionate Software Engineer with 2+ years of experience building web applications
and artificial intelligence systems.

Technical Skills:
Python, FastAPI, React, TypeScript, Docker, SQL, Machine Learning, Git

Experience:
Software Engineer | Acme Tech (2022 - Present)
- Developed REST APIs using FastAPI and Python
- Built responsive UI dashboards with React

Education:
B.Tech in Computer Science and Engineering | VTU (2018 - 2022)

Projects:
- CareerPilot AI: Intelligent job assistant and resume matcher
- Smart Doc Analyzer: Automated document classification tool
"""


def test_heuristic_parser_extracts_all_required_fields():
    profile = parse_resume_heuristically(SAMPLE_RESUME)
    assert profile.name is not None
    assert "Ashish" in profile.name
    assert profile.email == "ashish.vid@example.com"
    assert profile.phone is not None
    assert "9876543210" in profile.phone
    assert profile.designation is not None
    assert "Engineer" in profile.designation

    # Check skills
    lower_skills = [s.lower() for s in profile.skills]
    assert "python" in lower_skills
    assert "react" in lower_skills
    assert "fastapi" in lower_skills

    # Check experience & education
    assert profile.experience is not None
    assert len(profile.education) > 0
    assert len(profile.projects) > 0


def test_resume_agent_rejects_unsupported_extensions():
    agent = ResumeAgent()
    with pytest.raises(ValueError, match="Unsupported format"):
        agent.parse_from_bytes("resume.txt", b"some plain text")


def test_resume_agent_rejects_empty_files():
    agent = ResumeAgent()
    with pytest.raises(ValueError, match="too short"):
        agent.parse_from_text("Too short")

