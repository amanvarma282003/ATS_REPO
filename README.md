# ATS + Resume Intelligence Platform

## Project Overview

A bidirectional ATS + Resume Intelligence Platform that uses Knowledge Graph reasoning and LLM intelligence to match candidates with jobs and generate tailored resumes.

## Architecture

- **Backend**: Django + Django REST Framework
- **Knowledge Graph**: NetworkX
- **LLM**: Google Gemini
- **Resume Generation**: LaTeX → PDF
- **Frontend**: React (separate repository)

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL
- pdflatex (TeX Live)
- Node.js (for frontend)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ATS_Major
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install PostgreSQL (Arch Linux)**
   ```bash
   sudo pacman -Syu postgresql
   sudo -u postgres initdb -D /var/lib/postgres/data
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

5. **Create database**
   ```bash
   sudo -u postgres createdb ats_platform
   sudo -u postgres psql
   # In psql:
   CREATE USER ats_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE ats_platform TO ats_user;
   \q
   ```

6. **Install pdflatex (Arch Linux)**
   ```bash
   sudo pacman -Syu texlive-core texlive-bin texlive-latexextra
   ```

7. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key and other settings
   ```

8. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

9. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

10. **Run development server**
    ```bash
    python manage.py runserver
    ```

## Project Structure

```
ATS_Major/
├── accounts/           # User authentication and role management
├── candidates/         # Candidate profiles, projects, skills
├── recruiters/         # Job postings, applications, feedback
├── knowledge_graph/    # NetworkX graph construction and reasoning
├── resume_engine/      # LaTeX template management and PDF generation
├── llm_service/        # Gemini API integration and prompt management
├── ats_backend/        # Django project settings
├── manage.py
├── requirements.txt
├── .env.example
├── work.md             # Project specification
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

1. Read `rough_note.md` for complete technical analysis
2. Follow phase-based development plan in rough_note.md
3. Test each component independently
4. Integrate and run end-to-end tests

## Security Notes

- LaTeX input validation to prevent injection attacks
- LLM prompt separation (system vs user content)
- JWT-based authentication
- Role-based access control

## Documentation

- `work.md` - Complete project specification
- `rough_note.md` - In-depth technical analysis and decision log

## License

[To be determined]
