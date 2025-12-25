#!/bin/bash

echo "=== Testing Resume Upload and Autofill ==="

echo "1. Getting authentication token..."
CANDIDATE_TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"candidate_test@example.com","password":"testpass123"}' \
  | jq -r '.tokens.access')

if [ "$CANDIDATE_TOKEN" == "null" ] || [ -z "$CANDIDATE_TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi

echo "Token obtained"

echo ""
echo "2. Uploading resume text for parsing..."

RESUME_TEXT="John Doe
Email: john.doe@example.com
Phone: +1-555-0123

EXPERIENCE:
Senior Backend Engineer at Tech Corp (2020-2023)
- Built scalable REST APIs using Django and PostgreSQL
- Implemented microservices architecture with Docker and Kubernetes
- Led team of 5 engineers in developing payment processing system

PROJECTS:
E-commerce Platform: Developed full-stack e-commerce application with Django backend. Implemented user authentication, shopping cart, and payment gateway integration. Achieved 50,000+ daily active users.

Recommendation Engine: Built ML-based recommendation system using Python and scikit-learn. Improved user engagement by 35%.

SKILLS:
Python, Django, REST API, PostgreSQL, Docker, Kubernetes, Machine Learning, scikit-learn, AWS, Git"

curl -s http://127.0.0.1:8000/api/candidate/profile/upload_resume/ \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" \
  -d "{\"resume_text\": $(echo "$RESUME_TEXT" | jq -Rs .)}" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data, indent=2))"

echo ""
echo "=== Test Complete ==="
