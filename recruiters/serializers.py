from rest_framework import serializers
from .models import JobDescription, Application, RecruiterFeedback
from candidates.serializers import CandidateProfileSerializer


class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for JobDescription model."""
    recruiter_email = serializers.EmailField(source='recruiter.email', read_only=True)
    required_competencies = serializers.SerializerMethodField()
    
    class Meta:
        model = JobDescription
        fields = ['id', 'recruiter', 'recruiter_email', 'title', 'company', 'description',
                  'competencies', 'required_skills', 'optional_skills', 'required_competencies',
                  'status', 'posted_at', 'updated_at']
        read_only_fields = ['id', 'recruiter', 'posted_at', 'updated_at']
    
    def get_required_competencies(self, obj):
        """Return required_skills as required_competencies for frontend compatibility."""
        return obj.required_skills if obj.required_skills else []
    
    def create(self, validated_data):
        """Handle required_competencies input from frontend."""
        # The frontend sends required_competencies, we need to store it as required_skills
        if 'required_competencies' in self.initial_data:
            validated_data['required_skills'] = self.initial_data['required_competencies']
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Handle required_competencies input from frontend."""
        if 'required_competencies' in self.initial_data:
            validated_data['required_skills'] = self.initial_data['required_competencies']
        return super().update(instance, validated_data)


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
