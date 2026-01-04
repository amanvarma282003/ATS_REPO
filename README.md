# ATS + Resume Intelligence Platform

## Project Overview

A bidirectional ATS + Resume Intelligence Platform that uses Knowledge Graph reasoning and LLM intelligence to match candidates with jobs and generate tailored resumes.

## Architecture

- **Backend**: Django + Django REST Framework
- **Database**: SQLite (development)
- **Knowledge Graph**: NetworkX
- **LLM**: Google Gemini (2.5 Flash with fallback cascade)
- **Resume Generation**: LaTeX → PDF (Dockerized service)
- **Frontend**: React + TypeScript

## Setup Instructions

### Prerequisites

- Python 3.10+
- Docker (for LaTeX service)
- Node.js 16+ (for frontend)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/A-Akhil/ATS_Proj.git
   cd ATS_Major
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```

4. **Build and start LaTeX service (Docker)**
   ```bash
   cd latex-to-pdf
   docker build -t latex-service .
   docker run -d --name latex-service --restart unless-stopped -p 8006:8006 -v "$(pwd)/../resumes:/app/resumes" latex-service
   cd ..
   ```
   The Docker container will auto-start on system reboot.

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start Django backend**
   ```bash
   python manage.py runserver
   ```

8. **Start React frontend (in separate terminal)**
   ```bash
   cd frontend
   npm install
   npm start
   ```

The application will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- LaTeX Service: http://localhost:8006

## Project Structure

```
ATS_Major/
├── accounts/           # User authentication and role management
├── candidates/         # Candidate profiles, projects, skills
├── recruiters/         # Job postings, applications, feedback
├── knowledge_graph/    # NetworkX graph construction and reasoning
├── resume_engine/      # Resume generation and LaTeX management
├── llm_service/        # Gemini API integration and fallback logic
├── latex-to-pdf/       # Dockerized LaTeX compilation service
├── frontend/           # React + TypeScript UI
├── ats_backend/        # Django project settings
├── manage.py
├── requirements.txt
├── db.sqlite3          # SQLite database (not committed)
├── .env.example
└── rough_note.md       # Technical analysis and design decisions
```

## Key Features

### For Candidates
- Create structured profile (projects, skills, tools, domains)
- Paste job description → Generate tailored resume
- Download ATS-friendly PDF resumes
- Apply to jobs with auto-generated resumes
- Track application status

### For Recruiters
- Post job descriptions
- View candidate applications with match explanations
- See evidence-based reasoning (graph paths)
- Provide feedback (shortlist/reject)
- System learns from feedback

## Core Architecture Principles

1. **Knowledge Graph First**: Structured data in graph format is the source of truth
2. **LLM Second**: LLM reasons over graph data, doesn't replace it
3. **Resume Last**: PDF resumes are derived outputs, not primary data

## API Endpoints (Overview)

### Authentication
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`

### Candidate
- `GET/PUT /api/candidate/profile/`
- `POST /api/resume/generate/`
- `POST /api/jobs/{id}/apply/`

### Recruiter
- `POST /api/recruiter/jobs/`
- `GET /api/recruiter/jobs/{id}/candidates/`
- `POST /api/recruiter/candidates/{id}/feedback/`

## Development Workflow

1. Read `rough_note.md` for complete technical analysis and implementation details
2. Backend runs on port 8000, frontend on 3000, LaTeX service on 8006
3. SQLite database auto-created on first migration
4. Docker container for LaTeX service handles all PDF generation

## Technical Highlights

- **Multi-model LLM cascade**: Automatic fallback from Gemini 2.5 Flash → 3 Flash → 2.5 Flash Lite → Gemma 3
- **Quota management**: Per-model daily limits with automatic rotation
- **Auto-restart**: LaTeX Docker container configured with `unless-stopped` policy
- **Resume history**: Full versioning with smart label generation
- **Knowledge graph reasoning**: Evidence-based candidate-job matching

## Security Notes

- LaTeX input validation to prevent injection attacks
- LLM prompt separation (system vs user content)
- JWT-based authentication with refresh tokens
- Role-based access control
- API keys stored in .env (never committed)

## Documentation

- `rough_note.md` - Complete technical analysis, architecture decisions, and implementation log
- `BACKEND_STATUS.md` - Backend API reference and completion status
- `API_REFERENCE.md` - Detailed API documentation

## License

[To be determined]
