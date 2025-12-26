import os
from typing import Any, Dict, Optional, Set

from recruiters.models import JobDescription

_TEMPLATE_CACHE: Optional[str] = None


def build_candidate_snapshot(profile, selected_content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Construct a snapshot of the candidate profile for resume/application storage."""
    selected_project_ids: Set[int] = set()
    selected_skill_ids: Set[int] = set()

    if selected_content:
        selected_project_ids = set(selected_content.get('project_ids', []))
        selected_skill_ids = set(selected_content.get('skill_ids', []))

    projects = []
    for project in profile.projects.all():
        projects.append({
            'id': project.id,
            'title': project.title,
            'description': project.description,
            'outcomes': project.outcomes or [],
            'duration_start': project.duration_start.isoformat() if project.duration_start else None,
            'duration_end': project.duration_end.isoformat() if project.duration_end else None,
            'is_selected': project.id in selected_project_ids,
        })

    skills = []
    for candidate_skill in profile.candidate_skills.select_related('skill'):
        skills.append({
            'id': candidate_skill.skill.id,
            'name': candidate_skill.skill.name,
            'category': candidate_skill.skill.category,
            'proficiency_level': candidate_skill.proficiency_level,
            'years_of_experience': float(candidate_skill.years_of_experience or 0),
            'is_selected': candidate_skill.skill.id in selected_skill_ids,
        })

    tools = []
    for project in profile.projects.all():
        for project_tool in project.project_tools.select_related('tool'):
            tool = project_tool.tool
            tools.append({
                'project_id': project.id,
                'name': tool.name,
                'category': tool.category,
            })

    candidate_data: Dict[str, Any] = {
        'full_name': profile.full_name,
        'email': profile.user.email,
        'phone': profile.phone,
        'location': profile.location,
        'preferred_roles': profile.preferred_roles,
        'summary': profile.summary,
        'linkedin': profile.linkedin,
        'github': profile.github,
        'education': profile.education,
        'experience': profile.experience,
        'publications': profile.publications,
        'awards': profile.awards,
        'extracurricular': profile.extracurricular,
        'patents': profile.patents,
        'custom_links': profile.custom_links,
        'projects': projects,
        'skills': skills,
        'tools': tools,
        'graph_recommendations': selected_content or {},
    }

    return candidate_data


def load_resume_template() -> str:
    """Load and cache the LaTeX resume template so repeated requests avoid disk IO."""
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'template.tex')
        with open(template_path, 'r') as template_file:
            _TEMPLATE_CACHE = template_file.read()
    return _TEMPLATE_CACHE


def build_job_context(job: JobDescription) -> Dict[str, Any]:
    """Return structured metadata for a job description to feed downstream services."""
    competencies = job.competencies or {}
    return {
        'id': job.id,
        'title': job.title,
        'company': job.company,
        'description': job.description,
        'required_competencies': competencies.get('required_competencies', []),
        'optional_competencies': competencies.get('optional_competencies', []),
    }
