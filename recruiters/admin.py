from django.contrib import admin
from .models import JobDescription, Application, RecruiterFeedback


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'recruiter', 'status', 'posted_at']
    search_fields = ['title', 'company', 'recruiter__email']
    list_filter = ['status', 'posted_at']
    readonly_fields = ['posted_at', 'updated_at']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'status', 'applied_at']
    search_fields = ['candidate__full_name', 'job__title']
    list_filter = ['status', 'applied_at']
    readonly_fields = ['applied_at', 'updated_at', 'resume_id']


@admin.register(RecruiterFeedback)
class RecruiterFeedbackAdmin(admin.ModelAdmin):
    list_display = ['application', 'action', 'created_at']
    search_fields = ['application__candidate__full_name', 'application__job__title']
    list_filter = ['action', 'created_at']
    readonly_fields = ['created_at']
