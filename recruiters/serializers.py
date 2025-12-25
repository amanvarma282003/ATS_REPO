from rest_framework import serializers
from .models import JobDescription, Application, RecruiterFeedback
from candidates.serializers import CandidateProfileSerializer


class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for JobDescription model."""
    recruiter_email = serializers.EmailField(source='recruiter.email', read_only=True)
    
    class Meta:
        model = JobDescription
        fields = ['id', 'recruiter', 'recruiter_email', 'title', 'company', 'description',
                  'competencies', 'required_skills', 'optional_skills', 'status',
                  'posted_at', 'updated_at']
        read_only_fields = ['id', 'recruiter', 'posted_at', 'updated_at']


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    candidate_info = CandidateProfileSerializer(source='candidate', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_company = serializers.CharField(source='job.company', read_only=True)
    
    class Meta:
        model = Application
        fields = ['id', 'candidate', 'candidate_info', 'job', 'job_title', 'job_company',
                  'resume_id', 'resume_version', 'generated_pdf_path', 'status',
                  'match_explanation', 'applied_at', 'updated_at']
        read_only_fields = ['id', 'resume_id', 'applied_at', 'updated_at']


class RecruiterFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for RecruiterFeedback model."""
    
    class Meta:
        model = RecruiterFeedback
        fields = ['id', 'application', 'action', 'reason', 'feedback_data', 'created_at']
        read_only_fields = ['id', 'created_at']
