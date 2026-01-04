from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
import logging
import os
import time

from candidates.models import CandidateProfile
from recruiters.models import JobDescription, Application
from knowledge_graph.graph_engine import KnowledgeGraph
from llm_service.gemini_service import llm_service
from resume_engine.generator import resume_generator
from .models import GeneratedResume
from .utils import build_candidate_snapshot, load_resume_template, build_job_context

logger = logging.getLogger(__name__)


def _resolve_job_context(job_id, jd_text):
    """Return (job, jd_data, source_enum) for generation/label flows."""
    if job_id:
        job = get_object_or_404(JobDescription, id=job_id)
        jd_data = build_job_context(job)
        return job, jd_data, GeneratedResume.Source.JOB
    if jd_text:
        jd_data = llm_service.parse_job_description(jd_text)
        jd_data['id'] = 'temp'
        return None, jd_data, GeneratedResume.Source.JD_TEXT
    raise ValueError('Either job_id or jd_text is required')


def _resolve_job_context_for_label(job_id, jd_text):
    """Fast version that only extracts title/company for label preview."""
    if job_id:
        job = get_object_or_404(JobDescription, id=job_id)
        return {
            'title': job.title,
            'company': job.company
        }
    if jd_text:
        # Use fast parser that only gets title/company
        return llm_service.parse_jd_for_label(jd_text)
    raise ValueError('Either job_id or jd_text is required')


def _build_label_metadata(candidate, jd_data):
    role = (jd_data.get('title') or 'Custom Role').strip()
    company = (jd_data.get('company') or 'Custom Company').strip()
    base_label = f"{role} - {company}" if company else role
    base_slug = slugify(base_label) or 'resume'
    existing_max = GeneratedResume.objects.filter(
        candidate=candidate,
        base_slug=base_slug
    ).aggregate(max_version=Max('version'))['max_version'] or 0
    next_version = existing_max + 1
    display_label = base_label if next_version == 1 else f"{base_label} - {next_version}"
    return {
        'base_label': base_label,
        'base_slug': base_slug,
        'next_version': next_version,
        'display_label': display_label,
    }


class GenerateResumeView(APIView):
    """
    API endpoint to generate resume for a specific job.
    POST /api/resume/generate/
    """
    permission_classes = [IsAuthenticated]
    MAX_RETRIES = 10
    
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
        
        job_id = request.data.get('job_id')
        jd_text = request.data.get('jd_text')
        try:
            job, jd_data, source = _resolve_job_context(job_id, jd_text)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Build knowledge graph
        kg = KnowledgeGraph()
        kg.build_candidate_graph(profile)
        
        # Select content based on JD
        selected_content = kg.select_resume_content(jd_data)
        
        # Build comprehensive candidate data for LLM
        candidate_data = build_candidate_snapshot(profile, selected_content)
        
        # Get LaTeX template
        template_content = load_resume_template()
        
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

        label_metadata = _build_label_metadata(profile, jd_data)
        generated_record = self._persist_generated_resume(
            profile=profile,
            job=job,
            jd_data=jd_data,
            source=source,
            resume_data=resume_data,
            selected_content=selected_content,
            label_metadata=label_metadata
        )
        
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
                'attempt': attempt_number,
                'display_label': generated_record.display_label,
                'version': generated_record.version,
                'source': generated_record.source,
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        else:
            # Just return resume without creating application
            logger.info(f"Attempt {attempt_number}: Resume generated (no application)")
            return Response({
                'message': 'Resume generated successfully',
                'resume_id': resume_data['resume_id'],
                'pdf_path': resume_data['pdf_path'],
                'attempt': attempt_number,
                'display_label': generated_record.display_label,
                'version': generated_record.version,
                'source': generated_record.source,
            }, status=status.HTTP_200_OK)

    def _persist_generated_resume(self, profile, job, jd_data, source, resume_data, selected_content, label_metadata):
        with transaction.atomic():
            qs = GeneratedResume.objects.select_for_update().filter(
                candidate=profile,
                base_slug=label_metadata['base_slug']
            )
            current_max = qs.aggregate(max_version=Max('version'))['max_version'] or 0
            version = current_max + 1
            display_label = label_metadata['base_label'] if version == 1 else f"{label_metadata['base_label']} - {version}"
            generated_resume = GeneratedResume.objects.create(
                candidate=profile,
                job=job,
                resume_id=resume_data['resume_id'],
                base_label=label_metadata['base_label'],
                base_slug=label_metadata['base_slug'],
                display_label=display_label,
                version=version,
                jd_title=jd_data.get('title', ''),
                jd_company=jd_data.get('company', ''),
                pdf_path=resume_data['pdf_path'],
                source=source,
                jd_snapshot=jd_data,
                graph_snapshot=selected_content,
            )
        return generated_resume


class DownloadResumeView(APIView):
    """
    API endpoint to download a generated resume.
    GET /api/resume/download/<resume_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resume_id):
        profile = get_object_or_404(CandidateProfile, user=request.user)

        generated_resume = profile.generated_resumes.filter(resume_id=resume_id).first()

        if generated_resume:
            pdf_path = generated_resume.pdf_path
        else:
            application = Application.objects.filter(
                candidate=profile,
                resume_id=resume_id
            ).first()

            if application:
                pdf_path = application.generated_pdf_path
            else:
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
            history = profile.generated_resumes.select_related('job')

            resumes = [
                {
                    'resume_id': record.resume_id,
                    'display_label': record.display_label,
                    'version': record.version,
                    'pdf_path': record.pdf_path,
                    'source': record.source,
                    'created_at': record.created_at,
                    'job_id': record.job.id if record.job else None,
                    'jd_title': record.jd_title,
                    'jd_company': record.jd_company,
                }
                for record in history
            ]
            
            return Response({
                'resumes': resumes
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResumeLabelPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_object_or_404(CandidateProfile, user=request.user)
        job_id = request.data.get('job_id')
        jd_text = request.data.get('jd_text')

        try:
            jd_data = _resolve_job_context_for_label(job_id, jd_text)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        label_data = _build_label_metadata(profile, jd_data)
        return Response({
            'base_label': label_data['base_label'],
            'display_label': label_data['display_label'],
            'next_version': label_data['next_version'],
        }, status=status.HTTP_200_OK)
