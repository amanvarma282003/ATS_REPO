from google import genai
from google.genai import types
from django.conf import settings
import json
import time
import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for interacting with Google Gemini LLM.
    Handles resume parsing, JD parsing, LaTeX generation, and shortlisting.
    """
    
    def __init__(self):
        # Get API key from environment (GEMINI_API_KEY) automatically
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT
    
    def _call_llm_with_retry(self, prompt: str, response_schema: Optional[Dict] = None) -> str:
        """
        Call LLM with retry logic.
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"LLM call failed after {self.max_retries} attempts: {str(e)}")
    
    def parse_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Parse job description into structured competencies.
        
        Returns:
        {
            "title": "...",
            "required_competencies": [{"name": "...", "description": "..."}],
            "optional_competencies": [{"name": "...", "description": "..."}],
            "required_skills": ["skill1", "skill2"],
            "optional_skills": ["skill3", "skill4"]
        }
        """
        prompt = f"""
You are parsing a job description into structured competencies.

### SYSTEM INSTRUCTIONS ###
Output ONLY valid JSON matching the exact schema below.
Do NOT add any explanation or commentary.
Do NOT invent information not present in the job description.

### JOB DESCRIPTION START ###
{jd_text}
### JOB DESCRIPTION END ###

### OUTPUT SCHEMA ###
{{
    "title": "extracted job title",
    "company": "company/employer name or empty string",
    "required_competencies": [
        {{"name": "competency name", "description": "brief description"}}
    ],
    "optional_competencies": [
        {{"name": "competency name", "description": "brief description"}}
    ],
    "required_skills": ["skill1", "skill2"],
    "optional_skills": ["skill3", "skill4"]
}}

### RULES ###
- Required competencies are must-haves mentioned as requirements
- Optional competencies are nice-to-haves or preferences
- Extract actual skills/technologies mentioned
- Keep descriptions brief (1 sentence max)
- Use consistent naming conventions
- Derive the company name from any "About the company" or header text; if truly missing, return an empty string (do NOT fabricate a fantasy name)

Output JSON only:
"""
        
        response_text = self._call_llm_with_retry(prompt)
        clean_response = response_text.strip()
        if clean_response.startswith('```'):
            clean_response = re.sub(r'^```(?:json)?', '', clean_response, flags=re.IGNORECASE).strip()
        if clean_response.endswith('```'):
            clean_response = clean_response[:clean_response.rfind('```')].strip()
        
        # Extract JSON from response
        try:
            # Try to find JSON in response
            start = clean_response.find('{')
            end = clean_response.rfind('}') + 1
            if start != -1 and end > start:
                json_text = clean_response[start:end]
                parsed_data = json.loads(json_text, strict=False)
                
                # Validate required fields
                if not isinstance(parsed_data.get('required_competencies'), list):
                    parsed_data['required_competencies'] = []
                if not isinstance(parsed_data.get('optional_competencies'), list):
                    parsed_data['optional_competencies'] = []
                if not isinstance(parsed_data.get('required_skills'), list):
                    parsed_data['required_skills'] = []
                if not isinstance(parsed_data.get('optional_skills'), list):
                    parsed_data['optional_skills'] = []
                if not isinstance(parsed_data.get('company'), str):
                    parsed_data['company'] = ''
                
                return parsed_data
            else:
                raise ValueError("No valid JSON found in response")
        except json.JSONDecodeError as e:
            preview = clean_response[:500]
            raise Exception(
                f"Failed to parse LLM response as JSON: {str(e)}\nResponse snippet: {preview}"
            )
    
    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Parse resume text into structured JSON.
        
        Returns:
        {
            "personal_info": {"name": "...", "email": "...", "phone": "..."},
            "projects": [{"title": "...", "description": "...", "outcomes": [...]}],
            "skills": [{"name": "...", "category": "TECHNICAL|SOFT|DOMAIN"}],
            "tools": [{"name": "...", "category": "LANGUAGE|FRAMEWORK|PLATFORM"}]
        }
        """
        prompt = f"""
You are parsing a resume into structured JSON.

### SYSTEM INSTRUCTIONS ###
Output ONLY valid JSON matching the exact schema below.
Do NOT add information not present in the resume.
If a field is missing, use empty string or empty array.

### RESUME TEXT START ###
{resume_text}
### RESUME TEXT END ###

### OUTPUT SCHEMA ###
{{
    "personal_info": {{
        "name": "full name",
        "email": "email@example.com",
        "phone": "phone number"
    }},
    "projects": [
        {{
            "title": "project title",
            "description": "project description",
            "outcomes": ["achievement 1", "achievement 2"]
        }}
    ],
    "skills": [
        {{"name": "skill name", "category": "TECHNICAL"}}
    ],
    "tools": [
        {{"name": "tool name", "category": "LANGUAGE"}}
    ]
}}

### RULES ###
- Extract only information explicitly stated
- Categorize skills as TECHNICAL, SOFT, or DOMAIN
- Categorize tools as LANGUAGE, FRAMEWORK, PLATFORM, or OTHER
- Preserve all quantifiable outcomes/achievements

Output JSON only:
"""
        
        response_text = self._call_llm_with_retry(prompt)
        
        # Extract and parse JSON
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_text = response_text[start:end]
                return json.loads(json_text)
            else:
                raise ValueError("No valid JSON found in response")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse resume JSON: {str(e)}\nResponse: {response_text}")
    
    def generate_latex_content(self, candidate_data: Dict[str, Any], 
                               selected_content: Dict[str, Any],
                               jd_title: str,
                               template_content: str) -> str:
        """
        Generate complete LaTeX resume document using template.
        
        Args:
            candidate_data: Full candidate profile data
            selected_content: Selected projects and skills IDs
            jd_title: Job title being applied for
            template_content: LaTeX template to fill
        
        Returns:
            Complete LaTeX document as string
            
        Raises:
            Exception if generation fails
        """
        prompt = f"""
You are a LaTeX resume generator. Fill the following LaTeX template with the user profile data.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid LaTeX code - NO markdown code blocks, NO explanations, NO additional text
2. Start directly with \\documentclass and end with \\end{{document}}
3. Use the EXACT packages from the template - DO NOT add, remove, or modify any \\usepackage commands
4. If a section has no usable data, omit that section entirely instead of writing placeholder text.
5. ESCAPE ALL SPECIAL CHARACTERS: Replace _ with \\_, & with \\&, % with \\%, $ with \\$, # with \\#
6. DO NOT use \\\\ (double backslash) after commands like \\name{{}} - it causes LaTeX errors
7. Keep section structure from template - do NOT add new sections or modify section titles
8. Use ONLY the custom commands defined in the template
9. Email addresses must be escaped: user\\_name@example.com not user_name@example.com

### LATEX TEMPLATE ###
{template_content}

### CANDIDATE DATA ###
{json.dumps(candidate_data, indent=2)}

### SELECTED CONTENT ###
Projects to include (by ID): {json.dumps(selected_content.get('project_ids', []))}
Skills to include (by ID): {json.dumps(selected_content.get('skill_ids', []))}

### JOB TITLE ###
Tailoring resume for: {jd_title}

IMPORTANT: Return ONLY the complete LaTeX document with candidate data filled in. Start with \\documentclass, no code fences. Use the EXACT packages from template above.
"""
        
        try:
            logger.debug("[LLM] Sending LaTeX generation request to Gemini...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            logger.debug("[LLM] LaTeX content received from Gemini")
            latex_code = response.text.strip()
            
            # Clean up any markdown code fences (like your code does)
            latex_code = re.sub(r'^```latex\s*', '', latex_code)
            latex_code = re.sub(r'^```\s*', '', latex_code)
            latex_code = re.sub(r'\s*```$', '', latex_code)
            latex_code = latex_code.strip()
            
            # Basic validation - just check it starts and ends correctly
            if not latex_code.startswith('\\documentclass'):
                raise ValueError("Generated LaTeX doesn't start with \\documentclass")
            if not latex_code.endswith('\\end{document}'):
                raise ValueError("Generated LaTeX doesn't end with \\end{document}")
            
            logger.debug("[LLM] LaTeX validation passed")
            return latex_code
            
        except Exception as e:
            logger.error(f"[LLM] LaTeX generation error: {str(e)}")
            raise Exception(f"Failed to generate LaTeX content: {str(e)}. Will retry.")
    
    def generate_match_explanation(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate human-readable explanation of candidate-job match.
        
        Returns:
        {
            "decision": "SHORTLIST"|"REVIEW"|"REJECT",
            "confidence": 0.0-1.0,
            "explanation": "...",
            "strengths": [...],
            "gaps": [...]
        }
        """
        prompt = f"""
You are evaluating a candidate-job match based on evidence from a knowledge graph.

### MATCH DATA ###
{json.dumps(match_data, indent=2)}

### SYSTEM INSTRUCTIONS ###
Based on the matched and missing competencies, provide:
1. Decision: SHORTLIST (80%+ match), REVIEW (50-80%), or REJECT (<50%)
2. Confidence score (0.0 to 1.0)
3. Brief explanation of the decision
4. List of strengths (matched competencies with evidence)
5. List of gaps (missing required competencies)

### OUTPUT FORMAT ###
{{
    "decision": "SHORTLIST",
    "confidence": 0.85,
    "explanation": "Candidate shows strong match...",
    "strengths": ["strength 1", "strength 2"],
    "gaps": ["gap 1", "gap 2"]
}}

Output JSON only:
"""
        
        response_text = self._call_llm_with_retry(prompt)
        
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_text = response_text[start:end]
                return json.loads(json_text)
            else:
                raise ValueError("No valid JSON found in response")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse match explanation JSON: {str(e)}\nResponse: {response_text}")


# Singleton instance
llm_service = LLMService()
