import re
from typing import List, Dict, Any, Optional
from app.models import ResumeProfile

COMMON_DESIGNATIONS = [
    "Software Engineer", "Software Developer", "Full Stack Developer",
    "Frontend Developer", "Backend Developer", "Python Developer",
    "Machine Learning Engineer", "AI Engineer", "Data Scientist",
    "Data Analyst", "Data Engineer", "DevOps Engineer", "Cloud Engineer",
    "Mobile Developer", "Android Developer", "iOS Developer", "React Developer",
    "Java Developer", "Node.js Developer", "QA Engineer", "Automation Engineer",
    "System Engineer", "Research Intern", "SDE Intern", "Software Engineering Intern"
]

TECH_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "R",
    "React", "React.js", "React Native", "Next.js", "Vue", "Vue.js", "Angular", "Svelte",
    "Node.js", "Express", "Django", "FastAPI", "Flask", "Spring Boot", "ASP.NET", "Ruby on Rails",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra", "Elasticsearch", "DynamoDB",
    "Docker", "Kubernetes", "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud", "Terraform", "Ansible",
    "Git", "GitHub", "GitLab", "CI/CD", "Jenkins", "GitHub Actions", "Linux", "Unix", "Bash",
    "Machine Learning", "Deep Learning", "Artificial Intelligence", "Data Science", "Natural Language Processing", "NLP",
    "Computer Vision", "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "Pandas", "NumPy", "Matplotlib", "Seaborn",
    "Large Language Models", "LLMs", "LangChain", "LlamaIndex", "Hugging Face", "Transformers", "OpenAI", "Gemini",
    "REST APIs", "GraphQL", "gRPC", "Microservices", "HTML", "CSS", "Tailwind CSS", "Bootstrap",
    "Agile", "Scrum", "Jira", "OOP", "Data Structures", "Algorithms"
]


def parse_resume_heuristically(text: str) -> ResumeProfile:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text_lower = text.lower()

    # 1. Email extraction
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    email = email_match.group(0).rstrip(".") if email_match else None

    # 2. Phone extraction
    phone_match = re.search(r"(?:(?:\+|0{0,2})91[\s-]?)?[6789]\d{9}|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", text)
    phone = phone_match.group(0) if phone_match else None

    # 3. Candidate Name extraction (usually appears prominently near the top)
    name = None
    for line in lines[:8]:
        clean = line.strip()
        if "@" in clean or "http" in clean or any(char.isdigit() for char in clean):
            continue
        if len(clean) > 35 or len(clean.split()) > 4:
            continue
        if any(h in clean.lower() for h in ["resume", "curriculum", "cv", "profile", "contact", "summary", "experience"]):
            continue
        words = clean.split()
        if len(words) >= 1 and all(w[0].isupper() for w in words if w.isalpha()):
            name = clean
            break

    # 4. Designation extraction
    designation = None
    for des in COMMON_DESIGNATIONS:
        if re.search(r"\b" + re.escape(des) + r"\b", text, re.IGNORECASE):
            designation = des
            break
    if not designation:
        for line in lines[:10]:
            if any(term in line.lower() for term in ["engineer", "developer", "analyst", "scientist", "architect", "intern"]):
                if len(line) < 50:
                    designation = line
                    break

    # 5. Skills extraction
    detected_skills: list[str] = []
    seen = set()
    for skill in TECH_SKILLS:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text, re.IGNORECASE):
            if skill.lower() not in seen:
                seen.add(skill.lower())
                detected_skills.append(skill)

    # 6. Experience extraction
    experience = None
    exp_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:relevant\s*)?experience", text, re.IGNORECASE)
    if exp_matches:
        experience = f"{exp_matches[0]} years"
    elif "fresher" in full_text_lower or "entry level" in full_text_lower:
        experience = "Fresher / Entry level"
    elif "intern" in full_text_lower or "internship" in full_text_lower:
        experience = "0-1 year (Intern)"
    else:
        experience = "1-2 years"

    # 7. Education extraction
    education: list[str] = []
    edu_patterns = [
        r"(?:bachelor|master|b\.tech|m\.tech|b\.e\.|m\.e\.|b\.sc|m\.sc|bca|mca|bba|mba|ph\.?d)[^.\n,;]*",
        r"(?:computer science|information technology|electronics|mechanical|data science)[^.\n,;]*"
    ]
    for pat in edu_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            edu_str = m.group(0).strip()
            if len(edu_str) > 3 and edu_str not in education:
                education.append(edu_str)
    if not education:
        for line in lines:
            if any(k in line.lower() for k in ["university", "college", "institute", "polytechnic", "degree"]):
                if len(line) < 80 and line not in education:
                    education.append(line)
    education = education[:3]

    # 8. Projects extraction
    projects: list[str] = []
    project_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^(?:projects?|personal projects?|key projects?)\b", line, re.IGNORECASE):
            project_idx = i
            break
    if project_idx != -1:
        for line in lines[project_idx + 1:project_idx + 8]:
            if re.match(r"^(?:skills|education|experience|certifications|awards|summary)\b", line, re.IGNORECASE):
                break
            if len(line) > 5 and not line.startswith("http"):
                projects.append(line.lstrip("-•* "))
    if not projects:
        for line in lines:
            if any(k in line.lower() for k in ["portal", "system", "app", "dashboard", "chatbot", "analyzer", "platform"]):
                if len(line) < 60 and line not in projects:
                    projects.append(line.lstrip("-•* "))
    projects = projects[:4]

    return ResumeProfile(
        name=name or "Candidate",
        email=email,
        phone=phone,
        designation=designation or "Software Engineer",
        skills=detected_skills or ["Python", "SQL", "Git"],
        experience=experience,
        education=education,
        projects=projects,
    )
