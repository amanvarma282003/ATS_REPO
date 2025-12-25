#!/bin/bash

# Test API endpoints for ATS Platform

echo "=== Testing ATS API Endpoints ==="
echo

# Step 1: Register a candidate
echo "1. Registering candidate..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "candidate_test@example.com",
    "username": "candidatetest",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "role": "CANDIDATE"
  }')
echo "$REGISTER_RESPONSE" | python3 -m json.tool
echo

# Step 2: Login to get token
echo "2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "candidate_test@example.com",
    "password": "testpass123"
  }')
echo "$LOGIN_RESPONSE" | python3 -m json.tool
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['tokens']['access'])")
echo "Token: $TOKEN"
echo

# Step 3: Create candidate profile
echo "3. Creating candidate profile..."
PROFILE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/candidate/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Candidate",
    "phone": "+1234567890",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/testcandidate",
    "github_url": "https://github.com/testcandidate",
    "preferred_roles": ["Software Engineer", "Backend Developer"]
  }')
echo "$PROFILE_RESPONSE" | python3 -m json.tool
echo

# Step 4: Add a project
echo "4. Adding a project..."
PROJECT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/candidate/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "E-commerce Platform",
    "description": "Built a scalable e-commerce platform using Django and React",
    "outcomes": ["Reduced page load time by 40%", "Handled 10k+ concurrent users"],
    "order": 1,
    "tool_ids": []
  }')
echo "$PROJECT_RESPONSE" | python3 -m json.tool
PROJECT_ID=$(echo "$PROJECT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo "Project ID: $PROJECT_ID"
echo

# Step 5: Add skills
echo "5. Adding skills..."
SKILL1=$(curl -s -X POST http://localhost:8000/api/candidate/skills/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "category": "TECHNICAL"
  }')
echo "$SKILL1" | python3 -m json.tool
SKILL1_ID=$(echo "$SKILL1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo

SKILL2=$(curl -s -X POST http://localhost:8000/api/candidate/skills/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Django",
    "category": "TECHNICAL"
  }')
echo "$SKILL2" | python3 -m json.tool
SKILL2_ID=$(echo "$SKILL2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo

# Step 6: Link skills to candidate
echo "6. Linking skills to candidate..."
if [ -n "$SKILL1_ID" ] && [ -n "$PROJECT_ID" ]; then
  CANDIDATE_SKILL=$(curl -s -X POST http://localhost:8000/api/candidate/candidate-skills/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"skill\": $SKILL1_ID,
      \"proficiency_level\": \"EXPERT\",
      \"years_of_experience\": 5,
      \"acquired_from_project\": $PROJECT_ID
    }")
  echo "$CANDIDATE_SKILL" | python3 -m json.tool
  echo
fi

# Step 7: Register a recruiter
echo "7. Registering recruiter..."
RECRUITER_REGISTER=$(curl -s -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "recruiter_test@example.com",
    "username": "recruitertest",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "role": "RECRUITER"
  }')
echo "$RECRUITER_REGISTER" | python3 -m json.tool
RECRUITER_TOKEN=$(echo "$RECRUITER_REGISTER" | python3 -c "import sys, json; print(json.load(sys.stdin)['tokens']['access'])")
echo

# Step 8: Create a job description
echo "8. Creating job description..."
JD_TEXT="We are looking for a Senior Backend Developer with 5+ years of experience in Python and Django. The ideal candidate should have experience building scalable web applications, working with REST APIs, and implementing microservices architecture."
JD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/recruiter/jobs/ \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Senior Backend Developer\",
    \"company\": \"Tech Corp\",
    \"description\": \"$JD_TEXT\",
    \"required_skills\": [\"Python\", \"Django\", \"REST APIs\"],
    \"optional_skills\": [\"Docker\", \"Kubernetes\"],
    \"status\": \"ACTIVE\"
  }")
echo "$JD_RESPONSE" | python3 -m json.tool
JOB_ID=$(echo "$JD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo "Job ID: $JOB_ID"
echo

# Step 9: Generate resume for the job
if [ -n "$JOB_ID" ]; then
  echo "9. Generating resume for job..."
  RESUME_RESPONSE=$(curl -s -X POST http://localhost:8000/api/resume/generate/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"job_id\": $JOB_ID
    }")
  echo "$RESUME_RESPONSE" | python3 -m json.tool
  echo
fi

echo "=== Test Complete ==="
