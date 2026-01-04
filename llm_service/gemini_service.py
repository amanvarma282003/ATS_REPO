from google import genai
from google.genai import types
from django.conf import settings
from django.db.models import F
from django.utils import timezone
import hashlib
import json
import time
import os
import re
import logging
from typing import Dict, Any, Optional, List

from .models import LLMUsage

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for interacting with Google Gemini LLM.
    Handles resume parsing, JD parsing, LaTeX generation, and shortlisting.
    """
    
    def __init__(self):
        configured_keys: List[str] = getattr(settings, 'GEMINI_API_KEYS', [])
        if not configured_keys:
            raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEYS or GEMINI_API_KEY env vars.")

        self.api_keys = configured_keys
        self.clients = {key: genai.Client(api_key=key) for key in self.api_keys}
        self.api_key_fingerprints = {
            key: self._fingerprint_api_key(key) for key in self.api_keys
        }
        self.model_cascade = [
            "gemini-2.5-flash",
            "gemini-3-flash",
            "gemini-2.5-flash-lite",
            "gemma-3-27b-it",
        ]
        self.model_limits = {
            "gemini-2.5-flash": 20,
            "gemini-3-flash": 20,
            "gemini-2.5-flash-lite": 20,
            "gemma-3-27b-it": 14400,
        }
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT
    
    def _fingerprint_api_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]

    def _is_quota_error(self, error: Exception) -> bool:
        message = str(error).upper()
        return any(keyword in message for keyword in ["RESOURCE_EXHAUSTED", "QUOTA", "429"])

    def _claim_usage_slot(self, model_name: str, api_key: str) -> bool:
        limit = self.model_limits.get(model_name)
        if not limit:
            return True

        fingerprint = self.api_key_fingerprints[api_key]
        usage, _ = LLMUsage.objects.get_or_create(
            model_name=model_name,
            api_key_fingerprint=fingerprint,
            date=timezone.now().date(),
            defaults={'count': 0},
        )

        updated = LLMUsage.objects.filter(
            pk=usage.pk,
            count__lt=limit,
        ).update(count=F('count') + 1, updated_at=timezone.now())

        return bool(updated)

    def _call_llm_with_retry(
        self,
        prompt: str,
        response_schema: Optional[Dict] = None,
        config: Optional[types.GenerateContentConfig] = None,
    ) -> str:
        """Call LLM with cascading models and API keys, reacting to quota limits.
        Tries all API keys for each model before moving to next model."""

        last_error: Optional[Exception] = None

        for model_index, model_name in enumerate(self.model_cascade):
            for key_index, api_key in enumerate(self.api_keys):
                client = self.clients[api_key]
                attempt = 0
                while attempt < self.max_retries:
                    if not self._claim_usage_slot(model_name, api_key):
                        last_error = Exception(
                            f"Daily quota reached for {model_name} using API key #{key_index + 1}"
                        )
                        logger.info(
                            "Daily quota reached for model %s (API key #%s). Skipping until reset.",
                            model_name,
                            key_index + 1,
                        )
                        break

                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config,
                        )
                        if key_index > 0 or model_index > 0:
                            logger.info(
                                "LLM request succeeded using model %s (API key #%s)",
                                model_name,
                                key_index + 1,
                            )
                        return response.text
                    except Exception as exc:
                        last_error = exc
                        quota_error = self._is_quota_error(exc)
                        attempt += 1

                        if not quota_error:
                            if attempt < self.max_retries:
                                time.sleep(2 ** (attempt - 1))
                                continue
                            raise Exception(
                                f"LLM call failed after {self.max_retries} attempts using {model_name} "
                                f"(API key #{key_index + 1}): {str(exc)}"
                            )

                        logger.warning(
                            "LLM quota exhausted for model %s (API key #%s). Moving to next API key if available.",
                            model_name,
                            key_index + 1,
                        )
                        break  # move to next API key for same model

            if model_index < len(self.model_cascade) - 1:
                logger.info(
                    "All API keys quota-limited for model %s. Trying next model...",
                    model_name,
                )

        raise Exception(
            "LLM call failed after exhausting all configured models and API keys: "
            f"{str(last_error) if last_error else 'unknown error'}"
        )
    
    def _call_llm_with_gemma_only(self, prompt: str) -> str:
        """
        Call LLM using only Gemma model to save Gemini quota.
        Used for simpler tasks like JD parsing.
        """
        gemma_model = "gemma-3-27b-it"
        last_error: Optional[Exception] = None
        
        for key_index, api_key in enumerate(self.api_keys):
            client = self.clients[api_key]
            attempt = 0
            
            while attempt < self.max_retries:
                if not self._claim_usage_slot(gemma_model, api_key):
                    last_error = Exception(
                        f"Daily quota reached for {gemma_model} using API key #{key_index + 1}"
                    )
                    logger.info(
                        "Daily quota reached for model %s (API key #%s). Trying next API key...",
                        gemma_model,
                        key_index + 1,
                    )
                    break
                
                try:
                    response = client.models.generate_content(
                        model=gemma_model,
                        contents=prompt,
                    )
                    if key_index > 0:
                        logger.info(
                            "JD parsing succeeded using %s (API key #%s)",
                            gemma_model,
                            key_index + 1,
                        )
                    return response.text
                except Exception as exc:
                    last_error = exc
                    quota_error = self._is_quota_error(exc)
                    attempt += 1
                    
                    if not quota_error:
                        if attempt < self.max_retries:
                            time.sleep(2 ** (attempt - 1))
                            continue
                        raise Exception(
                            f"Gemma call failed after {self.max_retries} attempts "
                            f"(API key #{key_index + 1}): {str(exc)}"
                        )
                    
                    logger.warning(
                        "Gemma quota exhausted for API key #%s. Trying next API key...",
                        key_index + 1,
                    )
                    break
        
        raise Exception(
            f"JD parsing failed after exhausting all API keys with {gemma_model}: "
            f"{str(last_error) if last_error else 'unknown error'}"
        )
    
    def parse_jd_for_label(self, jd_text: str) -> Dict[str, str]:
        """
        Lightweight parser that only extracts title and company for resume labeling.
        Uses Gemma model only. Much faster than full parse_job_description.
        
        Returns:
        {
            "title": "Job Title",
            "company": "Company Name"
        }
        """
        prompt = f"""
Extract ONLY the job title and company name from this job description.

### JOB DESCRIPTION ###
{jd_text}

### OUTPUT FORMAT ###
{{
    "title": "extracted job title",
    "company": "company name or empty string if not found"
}}

Output JSON only:
"""
        
        try:
            response_text = self._call_llm_with_gemma_only(prompt)
            
            # Extract JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_text = response_text[start:end]
                parsed = json.loads(json_text)
                return {
                    'title': parsed.get('title', 'Custom Role'),
                    'company': parsed.get('company', '')
                }
        except Exception as e:
            logger.warning(f"Fast label parse failed: {e}")
        
        # Fallback: try to extract title from first line
        lines = jd_text.strip().split('\n')
        title = lines[0][:100] if lines else 'Custom Role'
        return {'title': title, 'company': ''}

    def parse_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Parse job description into structured competencies.
        Uses only Gemma model to save Gemini RPD quota.
        
        Returns:
        {
            "title": "...",
            "required_competencies": [{"name": "...", "description": "..."}],
            "optional_competencies": [{"name": "...", "description": "..."}],
            "required_skills": ["skill1", "skill2"],
            "optional_skills": ["skill3", "skill4"]
        }
        """
        max_parse_retries = 3
        last_error = None
        
        for attempt in range(max_parse_retries):
            try:
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
    "required_skills": ["list ALL required skills/technologies/tools mentioned"],
    "optional_skills": ["list ALL optional/preferred skills mentioned"]
}}

### RULES ###
- Required competencies are must-haves mentioned as requirements
- Optional competencies are nice-to-haves or preferences
- Extract ALL skills/technologies/tools mentioned in the JD (programming languages, frameworks, databases, cloud platforms, methodologies, tools, etc.)
- Include every technical skill, soft skill, domain knowledge, certification, or qualification mentioned
- Do not limit the number of skills - extract everything relevant
- Keep descriptions brief (1 sentence max)
- Use consistent naming conventions (e.g., "JavaScript" not "JS", "Python 3" not "Python3")
- Derive the company name from any "About the company" or header text; if truly missing, return an empty string (do NOT fabricate a fantasy name)
- Be comprehensive - a typical JD should yield 10-20+ skills

Output JSON only:
"""
                
                # Use only Gemma model (last in cascade) to save Gemini quota
                response_text = self._call_llm_with_gemma_only(prompt)
                clean_response = response_text.strip()
                if clean_response.startswith('```'):
                    clean_response = re.sub(r'^```(?:json)?', '', clean_response, flags=re.IGNORECASE).strip()
                if clean_response.endswith('```'):
                    clean_response = clean_response[:clean_response.rfind('```')].strip()
                
                # Extract JSON from response
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
                    
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                preview = clean_response[:500] if 'clean_response' in locals() else 'N/A'
                logger.warning(
                    f"Parse attempt {attempt + 1}/{max_parse_retries} failed: {str(e)}\nResponse snippet: {preview}"
                )
                if attempt < max_parse_retries - 1:
                    time.sleep(1)
                    continue
        
        # All retries failed
        raise Exception(
            f"Failed to parse LLM response as JSON after {max_parse_retries} attempts: {str(last_error)}"
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
You are an expert ATS ingestion agent. Convert the resume below into structured JSON so our database can auto-populate every profile section.

### SYSTEM INSTRUCTIONS ###
- Output ONLY valid JSON that matches the schema exactly (no prose, no markdown fences).
- Use empty arrays when data is missing. Do NOT invent facts.
- Dates MUST be ISO strings in \"YYYY-MM\" or \"YYYY-MM-DD\" format.
- Achievements/bullets should be concise action-impact statements.

### RESUME TEXT START ###
{resume_text}
### RESUME TEXT END ###

### OUTPUT SCHEMA ###
{{
    "personal_info": {{
        "name": "Full legal name",
        "email": "email@example.com",
        "phone": "phone number or empty string",
        "location": "city, country"
    }},
    "summary": "Two to three sentence professional summary",
    "preferred_roles": ["Target role 1", "Target role 2"],
    "links": {{
        "linkedin": "https://...",
        "github": "https://...",
        "custom_links": [
            {{"label": "Portfolio", "url": "https://...", "description": "Optional context"}}
        ]
    }},
    "education": [
        {{
            "institution": "University name",
            "degree": "Degree + major",
            "location": "City, Country",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or Present",
            "gpa": "CGPA or empty",
            "highlights": ["Notable coursework, awards"]
        }}
    ],
    "experience": [
        {{
            "company": "Company or organization",
            "role": "Job title",
            "location": "City, Country",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or Present",
            "achievements": ["Action verb + metric impact bullets"]
        }}
    ],
    "projects": [
        {{
            "title": "Project name",
            "role": "Role or responsibility",
            "description": "2 sentence summary",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "achievements": ["Key result bullets"],
            "tools": ["Tool or technology"]
        }}
    ],
    "skills": [
        {{
            "name": "Skill name",
            "category": "TECHNICAL|SOFT|DOMAIN",
            "proficiency_level": "BEGINNER|INTERMEDIATE|EXPERT",
            "years_of_experience": 3.5
        }}
    ],
    "tools": [
        {{"name": "Tool/technology", "category": "LANGUAGE|FRAMEWORK|PLATFORM|OTHER"}}
    ],
    "publications": [
        {{
            "title": "Paper title",
            "venue": "Conference or journal",
            "date": "YYYY-MM",
            "doi": "doi or empty",
            "description": "One sentence summary"
        }}
    ],
    "awards": [
        {{
            "title": "Award name",
            "organization": "Issuer",
            "level": "International/National/etc",
            "date": "YYYY-MM",
            "description": "Context"
        }}
    ],
    "extracurricular": [
        {{
            "role": "Position held",
            "organization": "Club/Community",
            "location": "City, Country",
            "description": "Impact summary"
        }}
    ],
    "patents": [
        {{
            "title": "Patent title",
            "patent_number": "Identifier",
            "filing_date": "YYYY-MM",
            "grant_date": "YYYY-MM or empty",
            "description": "Short abstract",
            "inventors": "Comma-separated names"
        }}
    ]
}}

### RULES ###
- Derive preferred roles from objective/summary/skills if explicitly stated.
- Keep bullet arrays ordered by relevance; limit to 4 entries per section when possible.
- Move any URLs into either `links.linkedin`, `links.github`, or `links.custom_links`.
- Omit sections you cannot substantiate by returning an empty array.

Return JSON only:
"""
        
        response_text = self._call_llm_with_retry(prompt)
        clean_response = response_text.strip()
        if clean_response.startswith('```'):
            clean_response = re.sub(r'^```(?:json)?', '', clean_response, flags=re.IGNORECASE).strip()
        if clean_response.endswith('```'):
            clean_response = clean_response[:clean_response.rfind('```')].strip()
        
        # Extract and parse JSON
        try:
            start = clean_response.find('{')
            end = clean_response.rfind('}') + 1
            if start != -1 and end > start:
                json_text = clean_response[start:end]
                parsed = json.loads(json_text, strict=False)
                list_fields = [
                    'preferred_roles', 'education', 'experience', 'projects',
                    'skills', 'tools', 'publications', 'awards', 'extracurricular',
                    'patents'
                ]
                for field in list_fields:
                    if not isinstance(parsed.get(field), list):
                        parsed[field] = []
                if not isinstance(parsed.get('links'), dict):
                    parsed['links'] = {}
                return parsed
            else:
                raise ValueError("No valid JSON found in response")
        except json.JSONDecodeError as e:
            preview = clean_response[:500]
            raise Exception(f"Failed to parse resume JSON: {str(e)}\nResponse snippet: {preview}")
    
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
            latex_code = self._call_llm_with_retry(
                prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            ).strip()
            logger.debug("[LLM] LaTeX content received from Gemini")
            
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
        Uses only Gemma model to save Gemini RPD quota.
        
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
        
        response_text = self._call_llm_with_gemma_only(prompt)
        
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
