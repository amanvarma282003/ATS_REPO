from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import JobDescription, Application, RecruiterFeedback
from .serializers import (
    JobDescriptionSerializer,
    ApplicationSerializer,
    RecruiterFeedbackSerializer
)
from knowledge_graph.graph_engine import KnowledgeGraph
import logging

logger = logging.getLogger(__name__)


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
            return Application.objects.filter(job__recruiter=self.request.user)
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
