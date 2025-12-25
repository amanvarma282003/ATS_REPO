from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
import os
import time
import logging

from candidates.models import CandidateProfile, Project, CandidateSkill
from recruiters.models import JobDescription, Application
from knowledge_graph.graph_engine import KnowledgeGraph
from llm_service.gemini_service import llm_service
from resume_engine.generator import resume_generator

logger = logging.getLogger(__name__)


class GenerateResumeView(APIView):
    """
    API endpoint to generate resume for a specific job.
    POST /api/resume/generate/
    """
    permission_classes = [IsAuthenticated]
    MAX_RETRIES = 3
    
    def post(self, request):
        # Retry entire generation pipeline
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._generate_resume(request, attempt + 1)
            except Exception as e:
                last_error = e
                logger.warning(f"Resume generation attempt {attempt + 1}/{self.MAX_RETRIES} failed: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
        
        # All retries failed
        return Response(
            {'error': f'Resume generation failed after {self.MAX_RETRIES} attempts: {str(last_error)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def _generate_resume(self, request, attempt_number):
        logger.info(f"Starting resume generation attempt {attempt_number}/{self.MAX_RETRIES}")
        
        # Get candidate profile
        profile = get_object_or_404(CandidateProfile, user=request.user)
        
        # Get job description
        job_id = request.data.get('job_id')
        jd_text = request.data.get('jd_text')
        
        if job_id:
            job = get_object_or_404(JobDescription, id=job_id)
            jd_data = {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'required_competencies': job.competencies.get('required_competencies', []),
                'optional_competencies': job.competencies.get('optional_competencies', []),
            }
        elif jd_text:
            # Parse JD text using LLM
            jd_data = llm_service.parse_job_description(jd_text)
            jd_data['id'] = 'temp'
        else:
            return Response({
                'error': 'Either job_id or jd_text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Build knowledge graph
        kg = KnowledgeGraph()
        kg.build_candidate_graph(profile)
        
        # Select content based on JD
        selected_content = kg.select_resume_content(jd_data)
        
        # Get full candidate data
        projects = Project.objects.filter(
            id__in=selected_content['project_ids']
        ).values('id', 'title', 'description', 'outcomes')
        
        skills = CandidateSkill.objects.filter(
            skill_id__in=selected_content['skill_ids']
        ).select_related('skill').values(
            'skill__name', 'proficiency_level', 'years_of_experience'
        )
        
        candidate_data = {
            'full_name': profile.full_name,
            'email': profile.user.email,
            'phone': profile.phone,
            'location': profile.location,
            'projects': list(projects),
            'skills': list(skills),
        }
        
        # Get LaTeX template
        template_path = os.path.join(os.path.dirname(__file__), '..', 'template.tex')
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Generate complete LaTeX document using LLM
        logger.info(f"Attempt {attempt_number}: Generating LaTeX document with Gemini")
        latex_document = llm_service.generate_latex_content(
            candidate_data,
            selected_content,
            jd_data['title'],
            template_content
        )
        logger.info(f"Attempt {attempt_number}: LaTeX document generated successfully")
        
        # Generate PDF from LaTeX
        logger.info(f"Attempt {attempt_number}: Compiling LaTeX to PDF")
        resume_data = resume_generator.generate_resume(
            candidate_data,
            latex_document,
            profile.id
        )
        logger.info(f"Attempt {attempt_number}: PDF generated successfully")
        
        # Create or update application if job_id provided
        if job_id:
            match_explanation = llm_service.generate_match_explanation(selected_content)
            application, created = Application.objects.update_or_create(
                candidate=profile,
                job=job,
                defaults={
                    'resume_id': resume_data['resume_id'],
                    'generated_pdf_path': resume_data['pdf_path'],
                    'resume_version': candidate_data,
                    'match_explanation': match_explanation
                }
            )
            
            logger.info(f"Attempt {attempt_number}: Resume generation completed successfully")
            return Response({
                'message': 'Resume generated and application created',
                'resume_id': resume_data['resume_id'],
                'pdf_path': resume_data['pdf_path'],
                'application_id': application.id,
                'match_explanation': match_explanation,
                'attempt': attempt_number
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        else:
            # Just return resume without creating application
            logger.info(f"Attempt {attempt_number}: Resume generated (no application)")
            return Response({
                'message': 'Resume generated successfully',
                'resume_id': resume_data['resume_id'],
                'pdf_path': resume_data['pdf_path'],
                'attempt': attempt_number
            }, status=status.HTTP_200_OK)


class DownloadResumeView(APIView):
    """
    API endpoint to download a generated resume.
    GET /api/resume/download/<resume_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resume_id):
        profile = get_object_or_404(CandidateProfile, user=request.user)

        # Attempt to find an application record first (job-linked generation)
        application = Application.objects.filter(
            candidate=profile,
            resume_id=resume_id
        ).first()

        if application:
            pdf_path = application.generated_pdf_path
        else:
            # Handle JD-only generations: file stored under candidate folder
            pdf_path = os.path.join(
                settings.RESUME_STORAGE_PATH,
                f"{profile.id}/{resume_id}.pdf"
            )

        if not os.path.exists(pdf_path):
            return Response(
                {'error': 'Resume file not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(pdf_path, 'rb'),
            as_attachment=True,
            filename=f"resume_{resume_id}.pdf"
        )


class ResumeHistoryView(APIView):
    """
    API endpoint to list all generated resumes.
    GET /api/resume/history/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = get_object_or_404(CandidateProfile, user=request.user)
            applications = Application.objects.filter(candidate=profile).select_related('job')
            
            resumes = [
                {
                    'resume_id': app.resume_id,
                    'job_title': app.job.title,
                    'job_company': app.job.company,
                    'status': app.status,
                    'applied_at': app.applied_at,
                    'pdf_path': app.generated_pdf_path
                }
                for app in applications
            ]
            
            return Response({
                'resumes': resumes
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
