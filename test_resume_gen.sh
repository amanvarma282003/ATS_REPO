#!/bin/bash

echo "=== Testing Resume Generation with Retry Logic ==="
echo

# Get token
echo "1. Getting authentication token..."
TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"candidate_test@example.com","password":"testpass123"}' \
  | jq -r '.tokens.access')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get token. Make sure server is running and user exists."
  exit 1
fi

echo "Token obtained: ${TOKEN:0:20}..."
echo

# Generate resume
echo "2. Generating resume (with automatic retry up to 3 times)..."
echo "   This may take 15-45 seconds depending on retries needed..."
echo

RESULT=$(curl -s -X POST http://localhost:8000/api/resume/generate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1}')

echo "$RESULT" | python3 -m json.tool

# Check if PDF was created
RESUME_ID=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('resume_id', ''))" 2>/dev/null)

if [ -n "$RESUME_ID" ]; then
  echo
  echo "3. Success! Resume ID: $RESUME_ID"
  echo "   Checking if PDF file exists..."
  
  # Find the PDF file
  PDF_FILE=$(find resumes/ -name "${RESUME_ID}.pdf" 2>/dev/null | head -1)
  
  if [ -n "$PDF_FILE" ]; then
    echo "   PDF found: $PDF_FILE"
    ls -lh "$PDF_FILE"
    echo
    echo "4. Testing download endpoint..."
    curl -s -X GET "http://localhost:8000/api/resume/download/${RESUME_ID}/" \
      -H "Authorization: Bearer $TOKEN" \
      -o "/tmp/test_resume_${RESUME_ID}.pdf"
    
    if [ -f "/tmp/test_resume_${RESUME_ID}.pdf" ]; then
      echo "   Downloaded successfully to: /tmp/test_resume_${RESUME_ID}.pdf"
      ls -lh "/tmp/test_resume_${RESUME_ID}.pdf"
    fi
  else
    echo "   Warning: PDF file not found in resumes/ directory"
  fi
else
  echo
  echo "Failed to generate resume. Check the error message above."
  echo "The system automatically retries up to 3 times, so if this failed,"
  echo "it means all 3 attempts were unsuccessful."
fi

echo
echo "=== Test Complete ==="
