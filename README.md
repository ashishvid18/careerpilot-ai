# CareerPilot AI

**AI-powered career assistance, resume analysis, and job matching.**

CareerPilot AI is a full-stack application designed to help job seekers explore relevant opportunities, analyze resumes, understand job requirements, and track applications from one place.

The project combines a React and TypeScript frontend with a FastAPI backend, resume parsing, job-matching logic, an AI-powered chat service, and application tracking.

## Overview

Job searching often involves switching between resume tools, job boards, and application spreadsheets. CareerPilot AI brings several of these workflows together in one interface.

### Key Features

- **Resume Upload and Parsing** — Upload supported PDF and DOCX resumes for information extraction.
- **Job Search** — Search available job listings using the application's job search functionality.
- **Job Matching** — Rank job opportunities according to profile information, skills, and supported filters.
- **AI Career Chat** — Interact with the configured AI service for career-related assistance.
- **Application Tracker** — Save jobs and update their application statuses.
- **REST API** — Use FastAPI endpoints for health checks, resume processing, job discovery, matching, and application management.
- **Automated Testing** — Backend tests cover job matching, dataset integration, identifier validation, and application storage.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| AI integration | Gemini API |
| Resume processing | PDF and DOCX parsing |
| Job matching | Python-based matching logic |
| Data storage | SQLite |
| Job data | JSON dataset; Jooble integration code |
| Testing | pytest |
| Version control | Git and GitHub |

## Architecture

```text
┌────────────────────────────────┐
│       React + TypeScript       │
│           Vite UI              │
└───────────────┬────────────────┘
                │ HTTP / JSON
                ▼
┌────────────────────────────────┐
│          FastAPI API           │
├────────────────────────────────┤
│ Resume Parsing                 │
│ Job Search and Matching        │
│ AI Career Chat                 │
│ Application Management         │
└───────┬──────────────┬─────────┘
        │              │
        ▼              ▼
┌──────────────┐ ┌────────────────┐
│ JSON Job Data│ │ SQLite Storage │
└──────────────┘ └────────────────┘
        │
        ▼
┌────────────────────────────────┐
│ External Integrations          │
│ Gemini API / Jooble API        │
└────────────────────────────────┘
```

The diagram shows the main logical components. External integrations depend on configuration and availability; the diagram does not imply that every request requires an external API.

## Project Structure

```text
careerpilot-ai/
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   └── store.py
│   │   ├── services/
│   │   │   ├── gemini_service.py
│   │   │   ├── job_matcher.py
│   │   │   └── resume_parser.py
│   │   ├── config.py
│   │   ├── jooble_service.py
│   │   ├── main.py
│   │   └── models.py
│   ├── data/
│   │   └── jobs.json
│   ├── scraper/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

## Prerequisites

Install the following before running the application:

- Python 3.13, or another Python version supported by the project's dependencies.
- Node.js and npm.
- Git.
- A Gemini API key for AI functionality.
- A Jooble API key if you intend to use the external job integration.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/ashishvid18/careerpilot-ai.git
cd careerpilot-ai
```

### 2. Set up the backend

From the repository root, create a virtual environment:

**Windows — Command Prompt**

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create your local environment file by copying the example:

```bat
copy .env.example .env
```

Open `backend/.env` and configure the values you need:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGIN=http://localhost:5175

JOOBLE_API_KEY=your_jooble_api_key
JOOBLE_API_BASE_URL=https://in.jooble.org/api
```

Replace the placeholders with your own credentials. Never commit your actual `.env` file or expose API keys in frontend code.

Start the backend from the `backend` directory:

```bat
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Health endpoint: `http://127.0.0.1:8000/api/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

### 3. Set up the frontend

Open a second terminal from the repository root:

```bat
cd frontend
npm install
npm run dev
```

Vite prints the local URL in the terminal. Open that exact URL in your browser. The port may vary if the default port is already occupied.

For local development, make sure the backend CORS configuration allows the exact frontend origin being used.

### 4. Build the frontend

To verify the TypeScript code and generate production assets:

```bat
npm run build
```

To preview the generated frontend build locally:

```bat
npm run preview
```

The production assets are generated in `frontend/dist/`.

## API Reference

The following endpoints are implemented in the backend.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend health |
| POST | `/api/chat` | Send a message to the career chat service |
| POST | `/api/resume/parse` | Upload and parse a resume |
| GET | `/api/jobs/search` | Search job listings |
| POST | `/api/jobs/match` | Match a profile with relevant jobs |
| POST | `/api/applications` | Save a job application |
| GET | `/api/applications` | List saved applications |
| PATCH | `/api/applications/status` | Update an application's status |

Use `http://127.0.0.1:8000/docs` for the interactive API documentation, including request schemas and response details.

## Application Statuses

The application tracker supports the following statuses:

- `saved_demo`
- `submitted`
- `under_review`
- `interview`
- `rejected`
- `offer`
- `withdrawn`

The application storage layer prevents duplicate records for the same session and job combination.

## Running Tests

From the repository root, activate the backend virtual environment and run:

```bat
cd backend
python -m pytest tests -v
```

The current backend test suite includes job-matching tests, real-dataset integration, identifier validation, and application-storage tests.

To check the scraper's Python syntax:

```bat
python -m py_compile scraper/scrape_jobs.py
```

## Configuration and Security

- Keep API credentials in `backend/.env`.
- Use `.env.example` only for documenting configuration names and safe placeholders.
- Never expose private API keys in frontend environment variables or public repositories.
- Configure CORS for the specific frontend origins required by each environment.
- Validate uploaded files and enforce size limits before processing them.
- Use authenticated user identities and enforce per-user access to application records before deploying for multiple users.
- Configure persistent database storage when deploying SQLite, or migrate to a managed database where appropriate.
- Avoid returning internal exceptions or sensitive implementation details in API responses.

**Deployment note:** The local application is a development/demo implementation. Public deployment requires reviewing authentication, data isolation, database persistence, upload limits, API-key handling, and production CORS settings.

## Current Limitations

- Job relevance depends on the available job data and matching logic.
- External API features depend on valid credentials, service availability, and the implemented integration path.
- AI responses depend on the configured provider and its availability.
- The local application tracker uses a session identifier; this should not be treated as secure multi-user authentication.
- Successful local tests do not replace integration testing in a deployed environment.

## Future Improvements

Potential next steps include:

- Secure user authentication and isolated application histories.
- More comprehensive job-match explanations and skill-gap analysis.
- Improved resume feedback and career recommendations.
- Persistent production database hosting.
- Deployment automation and continuous integration.
- Live demonstration URL and application screenshots.

## Contributing

Contributions and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and add tests where appropriate.
4. Run the relevant tests and frontend build.
5. Submit a pull request describing the changes.

## License

No license has been specified yet. Add a `LICENSE` file before granting others explicit permission to reuse, modify, or redistribute the project.

## Repository

GitHub: https://github.com/ashishvid18/careerpilot-ai

Built as a full-stack AI career assistance project combining web development, API integration, resume processing, and job matching.
