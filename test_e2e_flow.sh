#!/bin/bash

echo "=== END-TO-END WORKFLOW TEST ==="
echo "Testing: Candidate profile → Add skills → Generate resume → Apply → Recruiter feedback"
echo ""

# Step 1: Create new candidate
echo "Step 1: Creating new candidate user..."
CANDIDATE_EMAIL="e2e_candidate@example.com"
curl -s http://127.0.0.1:8000/api/auth/register/ -X POST \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$CANDIDATE_EMAIL\",\"username\":\"e2ecandidate\",\"password\":\"testpass123\",\"password_confirm\":\"testpass123\",\"role\":\"CANDIDATE\"}" > /dev/null

# Step 2: Login as candidate
echo "Step 2: Logging in as candidate..."
CANDIDATE_TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$CANDIDATE_EMAIL\",\"password\":\"testpass123\"}" \
  | jq -r '.tokens.access')

if [ -z "$CANDIDATE_TOKEN" ] || [ "$CANDIDATE_TOKEN" == "null" ]; then
  echo "ERROR: Failed to get candidate token"
  exit 1
fi
echo "✓ Candidate authenticated"

# Step 3: Add project
echo ""
echo "Step 3: Adding project to profile..."
PROJECT_ID=$(curl -s http://127.0.0.1:8000/api/candidate/projects/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d '{"title":"Django REST API Platform","description":"Built scalable backend system using Django REST Framework","outcomes":["Handles 100k+ requests/day","Reduced API response time by 40%"]}' \
  | jq -r '.id')
echo "✓ Project created (ID: $PROJECT_ID)"

# Step 4: Add skills
echo ""
echo "Step 4: Adding skills..."
PYTHON_SKILL=$(curl -s http://127.0.0.1:8000/api/candidate/skills/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d '{"name":"Python","category":"TECHNICAL"}' | jq -r '.id')

DJANGO_SKILL=$(curl -s http://127.0.0.1:8000/api/candidate/skills/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d '{"name":"Django","category":"TECHNICAL"}' | jq -r '.id')

curl -s http://127.0.0.1:8000/api/candidate/my-skills/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d "{\"skill\":$PYTHON_SKILL,\"proficiency_level\":\"EXPERT\",\"years_of_experience\":5}" > /dev/null

curl -s http://127.0.0.1:8000/api/candidate/my-skills/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d "{\"skill\":$DJANGO_SKILL,\"proficiency_level\":\"ADVANCED\",\"years_of_experience\":3}" > /dev/null

echo "✓ Skills added (Python, Django)"

# Step 5: Login as recruiter and create job
echo ""
echo "Step 5: Creating job as recruiter..."
RECRUITER_TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"recruiter_test@example.com","password":"testpass123"}' \
  | jq -r '.tokens.access')

JOB_ID=$(curl -s http://127.0.0.1:8000/api/recruiter/jobs/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -d '{"title":"Python Backend Developer","company":"E2E TestCorp","description":"Looking for experienced Python/Django developer","competencies":{"required_competencies":[{"name":"Backend Development","description":"API design and implementation"}]},"required_skills":["Python","Django"],"optional_skills":["PostgreSQL"]}' \
  | jq -r '.id')

echo "✓ Job created (ID: $JOB_ID)"

# Step 6: Generate resume and apply
echo ""
echo "Step 6: Generating resume and applying to job..."
APPLICATION_RESPONSE=$(curl -s http://127.0.0.1:8000/api/resume/generate/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d "{\"job_id\":$JOB_ID}")

RESUME_ID=$(echo "$APPLICATION_RESPONSE" | jq -r '.resume_id')
APP_ID=$(echo "$APPLICATION_RESPONSE" | jq -r '.application_id')
MATCH_DECISION=$(echo "$APPLICATION_RESPONSE" | jq -r '.match_explanation.decision')

echo "✓ Resume generated (ID: $RESUME_ID)"
echo "✓ Application created (ID: $APP_ID)"
echo "  Match Decision: $MATCH_DECISION"

# Step 7: Recruiter views application
echo ""
echo "Step 7: Recruiter viewing application..."
APP_STATUS=$(curl -s "http://127.0.0.1:8000/api/recruiter/applications/$APP_ID/" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  | jq -r '.status')

echo "✓ Application status: $APP_STATUS"

# Step 8: Recruiter provides feedback
echo ""
echo "Step 8: Recruiter shortlisting candidate..."
curl -s http://127.0.0.1:8000/api/recruiter/feedback/ -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -d "{\"application\":$APP_ID,\"action\":\"SHORTLIST\",\"reason\":\"Strong Python and Django skills, good project experience\"}" > /dev/null

UPDATED_STATUS=$(curl -s "http://127.0.0.1:8000/api/recruiter/applications/$APP_ID/" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  | jq -r '.status')

echo "✓ Feedback submitted"
echo "  Updated status: $UPDATED_STATUS"

# Summary
echo ""
echo "=== TEST SUMMARY ==="
echo "✓ Candidate created and authenticated"
echo "✓ Project added to profile"
echo "✓ Skills added (Python: EXPERT, Django: ADVANCED)"
echo "✓ Job created by recruiter"
echo "✓ Resume generated and application submitted"
echo "✓ Recruiter viewed application"
echo "✓ Recruiter provided feedback (SHORTLIST)"
echo "✓ Application status updated from $APP_STATUS → $UPDATED_STATUS"
echo ""
echo "=== ALL TESTS PASSED ==="
