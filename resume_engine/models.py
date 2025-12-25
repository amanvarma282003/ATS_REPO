from django.db import models
from django.utils import timezone


class GeneratedResume(models.Model):
	class Source(models.TextChoices):
		JOB = 'JOB', 'Job'
		JD_TEXT = 'JD_TEXT', 'Job Description Text'

	candidate = models.ForeignKey(
		'candidates.CandidateProfile',
		on_delete=models.CASCADE,
		related_name='generated_resumes'
	)
	job = models.ForeignKey(
		'recruiters.JobDescription',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='generated_resumes'
	)
	resume_id = models.CharField(max_length=64, unique=True)
	base_label = models.CharField(max_length=255)
	base_slug = models.CharField(max_length=255)
	display_label = models.CharField(max_length=255)
	version = models.PositiveIntegerField(default=1)
	jd_title = models.CharField(max_length=255, blank=True)
	jd_company = models.CharField(max_length=255, blank=True)
	pdf_path = models.CharField(max_length=500)
	source = models.CharField(max_length=10, choices=Source.choices)
	jd_snapshot = models.JSONField(default=dict, blank=True)
	graph_snapshot = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(default=timezone.now)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['candidate', 'base_slug']),
		]

	def __str__(self):
		return f"{self.display_label} ({self.resume_id})"
