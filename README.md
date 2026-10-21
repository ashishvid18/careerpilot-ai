# CareerPilot AI
A conversational job-search assistant built with React, FastAPI, Gemini, and LangGraph (agent orchestration will be expanded in the next stage).

## Run on Windows
Prerequisites: Python 3.11+, Node.js 20+, Gemini API key.

Backend terminal:
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add GEMINI_API_KEY
uvicorn app.main:app --reload
```

Frontend terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Backend docs: http://127.0.0.1:8000/docs.

## Current scope
This is the runnable foundation: handcrafted responsive chat UI, Gemini chat endpoint, PDF/DOCX text extraction, Gemini structured resume parsing, and SQLite application table initialization. `backend/data/jobs.json` is intentionally empty until the real listing collection pipeline is implemented. This starter does not yet scrape 1,500–2,000 jobs or submit applications to employers.

## Security and truthfulness
Never commit `.env`. Resume content is untrusted data. Do not mark an employer application submitted unless an authorized integration returns a verifiable success response.
