import os

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .models import JobDescription, Application, RecruiterFeedback
from .serializers import (
    JobDescriptionSerializer,
    ApplicationSerializer,
    RecruiterFeedbackSerializer
)
from knowledge_graph.graph_engine import KnowledgeGraph
from llm_service.gemini_service import llm_service
from resume_engine.generator import resume_generator
from resume_engine.utils import load_resume_template, build_job_context
import logging

logger = logging.getLogger(__name__)


def _generate_pdf_for_application(application: Application) -> str:
    """Generate a PDF for the given application using stored snapshot data."""
    candidate_data = application.resume_version or {}
    if not candidate_data:
        raise ValueError('Application missing resume snapshot data.')

    selected_content = candidate_data.get('graph_recommendations') or {}
    template_content = load_resume_template()
    job_context = build_job_context(application.job)

    latex_document = llm_service.generate_latex_content(
        candidate_data,
        selected_content,
        job_context.get('title') or application.job.title,
        template_content
    )

    resume_payload = resume_generator.generate_resume(
        candidate_data,
        latex_document,
        application.candidate.id
    )

    application.resume_id = resume_payload['resume_id']
    application.generated_pdf_path = resume_payload['pdf_path']
    application.save(update_fields=['resume_id', 'generated_pdf_path', 'updated_at'])

    return resume_payload['pdf_path']


class JobDescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for JobDescription management.
    """
    serializer_class = JobDescriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get jobs for current recruiter."""
        if self.request.user.is_recruiter:
            return JobDescription.objects.filter(recruiter=self.request.user)
        # Candidates can see all active jobs
        return JobDescription.objects.filter(status=JobDescription.Status.ACTIVE)
    
    def perform_create(self, serializer):
        """Create job for current recruiter."""
        serializer.save(recruiter=self.request.user)
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get all applications for a specific job."""
        job = self.get_object()
        if job.recruiter != request.user and not request.user.is_staff:
            return Response({'error': 'Permission denied'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        applications = Application.objects.filter(job=job)
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def parse_jd(self, request):
        """Parse job description text and return structured competencies."""
        jd_text = request.data.get('jd_text')
        if not jd_text:
            return Response({'error': 'jd_text is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            parsed_data = llm_service.parse_job_description(jd_text)
            return Response(parsed_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"JD parsing failed: {e}")
            return Response({'error': f'Failed to parse job description: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Application management.
    """
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get applications based on user role."""
        if self.request.user.is_candidate:
            # Candidates see their own applications
            try:
                from candidates.models import CandidateProfile
                profile = CandidateProfile.objects.get(user=self.request.user)
                return Application.objects.filter(candidate=profile)
            except CandidateProfile.DoesNotExist:
                return Application.objects.none()
        elif self.request.user.is_recruiter:
            # Recruiters see applications to their jobs
            queryset = Application.objects.filter(job__recruiter=self.request.user)
            job_id = self.request.query_params.get('job_id')
            if job_id:
                try:
                    job_id = int(job_id)
                except (TypeError, ValueError):
                    return Application.objects.none()
                queryset = queryset.filter(job_id=job_id)
            return queryset
        return Application.objects.none()


class RecruiterFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RecruiterFeedback management.
    """
    serializer_class = RecruiterFeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get feedback for recruiter's applications."""
        if self.request.user.is_recruiter:
            return RecruiterFeedback.objects.filter(
                application__job__recruiter=self.request.user
            )
        return RecruiterFeedback.objects.none()
    
    def perform_create(self, serializer):
        """Create feedback and update application status."""
        feedback = serializer.save()
        
        # Update application status based on feedback action
        application = feedback.application
        action_to_status = {
            RecruiterFeedback.Action.SHORTLIST: Application.Status.SHORTLISTED,
            RecruiterFeedback.Action.REJECT: Application.Status.REJECTED,
            RecruiterFeedback.Action.INTERVIEW: Application.Status.INTERVIEWED,
            RecruiterFeedback.Action.HIRE: Application.Status.HIRED,
        }
        
        new_status = action_to_status.get(feedback.action)
        if new_status:
            application.status = new_status
            application.save()
        
        # Update knowledge graph weights based on feedback
        try:
            logger.info(f"Updating graph weights for feedback: {feedback.action} on application {application.id}")
            kg = KnowledgeGraph()
            kg.build_candidate_graph(application.candidate)
            
            # Convert feedback action to signal
            feedback_signal = {
                'action': feedback.action,
                'application_id': application.id,
                'job_id': application.job.id,
                'reason': feedback.reason
            }
            
            kg.update_weights_from_feedback(feedback_signal)
            logger.info("Graph weights updated successfully")
        except Exception as e:
            logger.error(f"Failed to update graph weights: {e}")
            # Don't fail the request if graph update fails


class RecruiterApplicationDownloadView(APIView):
    """Allow recruiters to download candidate resumes with lazy PDF generation."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        application = get_object_or_404(Application, pk=pk)

        if not request.user.is_recruiter or application.job.recruiter != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        pdf_path = application.generated_pdf_path
        if not pdf_path or not os.path.exists(pdf_path):
            try:
                pdf_path = _generate_pdf_for_application(application)
            except Exception as exc:
                logger.error(f"Failed to generate PDF for application {application.id}: {exc}")
                return Response({'error': 'Unable to generate resume PDF'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not os.path.exists(pdf_path):
            return Response({'error': 'Resume file not found'}, status=status.HTTP_404_NOT_FOUND)

        filename = f"application_{application.id}.pdf"
        return FileResponse(
            open(pdf_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
