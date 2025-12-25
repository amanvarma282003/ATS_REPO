from django.contrib import admin
from .models import GeneratedResume


@admin.register(GeneratedResume)
class GeneratedResumeAdmin(admin.ModelAdmin):
	list_display = ('display_label', 'candidate', 'resume_id', 'version', 'source', 'created_at')
	list_filter = ('source', 'created_at')
	search_fields = ('display_label', 'resume_id', 'candidate__full_name', 'candidate__user__email')
