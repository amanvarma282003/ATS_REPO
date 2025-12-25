# API Quick Reference

Base URL: `http://127.0.0.1:8000`

## Authentication

### Register
```bash
POST /api/auth/register/
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "password_confirm": "password123",
  "role": "CANDIDATE" | "RECRUITER"
}
```

### Login
```bash
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "user": {...},
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

## Candidate APIs

All require: `Authorization: Bearer <access_token>`

### Profile
```bash
# Get profile
GET /api/candidate/profile/

# Update profile
PUT /api/candidate/profile/
{
  "full_name": "John Doe",
  "phone": "+1-555-0123",
  "location": "San Francisco, CA"
}
```

### Resume Upload (Autofill)
```bash
POST /api/candidate/profile/upload_resume/
{
  "resume_text": "John Doe\nEmail: john@example.com\n..."
}

Response:
{
  "message": "Resume parsed successfully",
  "projects_created": ["Project 1"],
  "skills_created": ["Python", "Django"],
  "tools_created": ["Docker"],
  "profile": {...}
}
```

### Projects
```bash
# List projects
GET /api/candidate/projects/

# Create project
POST /api/candidate/projects/
{
  "title": "E-commerce Platform",
  "description": "Built scalable REST API",
  "outcomes": ["10k+ DAU", "99.9% uptime"]
}
```

### Skills
```bash
# List all skills
GET /api/candidate/skills/

# Create skill
POST /api/candidate/skills/
{
  "name": "Python",
  "category": "TECHNICAL"
}

# Link skill to profile
POST /api/candidate/my-skills/
{
  "skill": 1,
  "proficiency_level": "EXPERT",
  "years_of_experience": 5
}
```

## Recruiter APIs

All require: `Authorization: Bearer <access_token>` (Recruiter role)

### Jobs
```bash
# List jobs
GET /api/recruiter/jobs/

# Create job
POST /api/recruiter/jobs/
{
  "title": "Senior Backend Engineer",
  "company": "TechCorp",
  "description": "Looking for experienced developer...",
  "competencies": {
    "required_competencies": [
      {"name": "Backend Development", "description": "API design"}
    ],
    "optional_competencies": [
      {"name": "DevOps", "description": "CI/CD"}
    ]
  },
  "required_skills": ["Python", "Django"],
  "optional_skills": ["Docker"]
}
```

### Applications
```bash
# View all applications for recruiter's jobs
GET /api/recruiter/applications/

# View applications for specific job
GET /api/recruiter/applications/?job_id=1

# View specific application
GET /api/recruiter/applications/1/

Response:
{
  "id": 1,
  "candidate_info": {...},
  "job_title": "Senior Backend Engineer",
  "status": "PENDING",
  "match_explanation": {
    "decision": "RECOMMEND",
    "confidence": 0.85,
    "explanation": "...",
    "strengths": [...],
    "gaps": [...]
  },
  "resume_id": "...",
  "generated_pdf_path": "..."
}
```

### Feedback
```bash
POST /api/recruiter/feedback/
{
  "application": 1,
  "action": "SHORTLIST",  # SHORTLIST | REJECT | INTERVIEW | HIRE
  "reason": "Strong technical skills"
}

# Automatically updates:
# - Application status
# - Knowledge graph weights
```

## Resume APIs

Requires: `Authorization: Bearer <access_token>` (Candidate role)

### Generate Resume
```bash
POST /api/resume/generate/
{
  "job_id": 1  # OR "jd_text": "Job description..."
}

Response:
{
  "message": "Resume generated successfully",
  "resume_id": "uuid-here",
  "pdf_path": "resumes/...",
  "application_id": 1,  # if job_id provided
  "match_explanation": {...},
  "attempt": 1  # Which retry attempt succeeded
}

# Features:
# - Automatic retry (up to 3 attempts)
# - Knowledge graph-based content selection
# - LLM-generated LaTeX document
# - PDF compilation
# - Match explanation
```

### Download Resume
```bash
GET /api/resume/download/<resume_id>/

Response: PDF file
Content-Type: application/pdf
Content-Disposition: attachment; filename="resume_<resume_id>.pdf"
```

## Common Response Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Testing with cURL

### Quick Test Flow
```bash
# 1. Register candidate
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password":"pass123","password_confirm":"pass123","role":"CANDIDATE"}'

# 2. Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}' \
  | jq -r '.tokens.access')

# 3. Add project
curl -X POST http://127.0.0.1:8000/api/candidate/projects/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Project","description":"Test","outcomes":[]}'

# 4. Generate resume
curl -X POST http://127.0.0.1:8000/api/resume/generate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jd_text":"Looking for Python developer"}'
```

## Environment Variables

Required in `.env` or environment:
```
GEMINI_API_KEY=your-api-key-here
LATEX_SERVICE_URL=http://localhost:8006/convert
SECRET_KEY=your-django-secret-key
DEBUG=True  # False in production
```

## Running Tests

```bash
# Ensure Django server is running
python manage.py runserver

# Run test scripts
./test_resume_gen.sh
./test_resume_upload.sh
./test_e2e_flow.sh
```

## Notes

- All POST/PUT requests require `Content-Type: application/json`
- JWT tokens expire after 24 hours (access token)
- External LaTeX service must be running at localhost:8006
- Resume generation typically takes 10-30 seconds
- System automatically retries failed generations (max 3 attempts)
- Graph weights update asynchronously on feedback submission
