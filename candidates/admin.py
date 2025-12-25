from django.contrib import admin
from .models import (
    CandidateProfile,
    Project,
    Skill,
    CandidateSkill,
    Tool,
    ProjectTool,
    Domain
)


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'location', 'created_at']
    search_fields = ['full_name', 'user__email']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'candidate', 'duration_start', 'duration_end', 'order']
    search_fields = ['title', 'candidate__full_name']
    list_filter = ['duration_start', 'duration_end']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_verified', 'created_at']
    search_fields = ['name']
    list_filter = ['category', 'is_verified']


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'skill', 'proficiency_level', 'years_of_experience']
    search_fields = ['candidate__full_name', 'skill__name']
    list_filter = ['proficiency_level']


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_at']
    search_fields = ['name']
    list_filter = ['category']


@admin.register(ProjectTool)
class ProjectToolAdmin(admin.ModelAdmin):
    list_display = ['project', 'tool', 'created_at']
    search_fields = ['project__title', 'tool__name']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_domain', 'created_at']
    search_fields = ['name']
