from django.db import models
from django.conf import settings
from candidates.models import CandidateProfile


class JobDescription(models.Model):
    """
    Job postings created by recruiters.
    JD is parsed into competencies by LLM.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
    
    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_descriptions'
    )
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    description = models.TextField(
        help_text="Raw job description text"
    )
    competencies = models.JSONField(
        default=dict,
        help_text="Parsed competencies from LLM"
    )
    required_skills = models.JSONField(
        default=list,
        help_text="Required skills extracted from JD"
    )
    optional_skills = models.JSONField(
        default=list,
        help_text="Optional/nice-to-have skills"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    posted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'job_descriptions'
        ordering = ['-posted_at']
        verbose_name = 'Job Description'
        verbose_name_plural = 'Job Descriptions'
    
    def __str__(self):
        return f"{self.title} at {self.company}"


class Application(models.Model):
    """
    Applications submitted by candidates to jobs.
    Stores resume snapshot and generated PDF reference.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        REJECTED = 'REJECTED', 'Rejected'
        INTERVIEWED = 'INTERVIEWED', 'Interviewed'
        HIRED = 'HIRED', 'Hired'
    
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    job = models.ForeignKey(
        JobDescription,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    resume_id = models.CharField(
        max_length=100,
        help_text="UUID of the generated resume"
    )
    resume_version = models.JSONField(
        help_text="Snapshot of candidate data used in resume"
    )
    generated_pdf_path = models.CharField(
        max_length=500,
        help_text="Path to generated PDF file"
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING
    )
    match_explanation = models.JSONField(
        default=dict,
        help_text="LLM-generated explanation of why candidate matched"
    )
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'applications'
        unique_together = ['candidate', 'job']
        ordering = ['-applied_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
    
    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title}"


class RecruiterFeedback(models.Model):
    """
    Feedback provided by recruiters on applications.
    Used to update knowledge graph weights and preferences.
    """
    
    class Action(models.TextChoices):
        SHORTLIST = 'SHORTLIST', 'Shortlist'
        REJECT = 'REJECT', 'Reject'
        INTERVIEW = 'INTERVIEW', 'Interview'
        HIRE = 'HIRE', 'Hire'
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    action = models.CharField(
        max_length=10,
        choices=Action.choices
    )
    reason = models.TextField(
        blank=True,
        help_text="Optional reason for the action"
    )
    feedback_data = models.JSONField(
        default=dict,
        help_text="Structured data for graph weight updates"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recruiter_feedbacks'
        ordering = ['-created_at']
        verbose_name = 'Recruiter Feedback'
        verbose_name_plural = 'Recruiter Feedbacks'
    
    def __str__(self):
        return f"{self.action} - {self.application}"
