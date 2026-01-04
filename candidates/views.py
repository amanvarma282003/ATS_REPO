from decimal import Decimal, InvalidOperation
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from .models import (
    CandidateProfile,
    Project,
    Skill,
    CandidateSkill,
    Tool,
    Domain
)
from .serializers import (
    CandidateProfileSerializer,
    ProjectSerializer,
    SkillSerializer,
    CandidateSkillSerializer,
    ToolSerializer,
    DomainSerializer
)
from recruiters.models import JobDescription, Application, ApplicationPreview
from recruiters.serializers import ApplicationSerializer
from resume_engine.models import GeneratedResume
from knowledge_graph.graph_engine import KnowledgeGraph
from resume_engine.utils import build_candidate_snapshot, build_job_context
from llm_service.gemini_service import LLMService
import logging

logger = logging.getLogger(__name__)
llm_service = LLMService()


def _clean_string_list(values):
    if not isinstance(values, list):
        return []
    cleaned = []
    for item in values:
        if isinstance(item, str):
            text = item.strip()
            if text:
                cleaned.append(text)
    return cleaned


def _clean_text(value):
    return value.strip() if isinstance(value, str) else ''


def _normalize_entries(entries):
    normalized = []
    if not isinstance(entries, list):
        return normalized
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cleaned_entry = {}
        for key, value in entry.items():
            if isinstance(value, str):
                cleaned_entry[key] = value.strip()
            elif isinstance(value, list):
                cleaned_entry[key] = [
                    item.strip() if isinstance(item, str) else item
                    for item in value
                    if item not in (None, '')
                ]
            else:
                cleaned_entry[key] = value
        if cleaned_entry:
            normalized.append(cleaned_entry)
    return normalized


def _parse_date_string(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) == 7 and text.count('-') == 1:
        text = f"{text}-01"
    parsed = parse_date(text)
    return parsed


def _to_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _get_or_compute_preview(profile: CandidateProfile, job: JobDescription, *, force_refresh: bool = False):
    candidate_timestamp = profile.updated_at
    job_timestamp = job.updated_at

    preview = ApplicationPreview.objects.filter(candidate=profile, job=job).first()

    needs_refresh = (
        force_refresh
        or preview is None
        or preview.candidate_updated_at < candidate_timestamp
        or preview.job_updated_at < job_timestamp
    )

    if needs_refresh:
        kg = KnowledgeGraph()
        kg.build_candidate_graph(profile)
        jd_data = build_job_context(job)
        matching_result = kg.find_matching_paths(jd_data)
        selected_content = kg.select_resume_content(jd_data, matching_result=matching_result)

        preview, _ = ApplicationPreview.objects.update_or_create(
            candidate=profile,
            job=job,
            defaults={
                'match_strength': float(selected_content.get('match_strength') or 0.0),
                'required_coverage': matching_result.get('required_coverage') or '',
                'selected_projects': len(selected_content.get('project_ids', [])),
                'selected_skills': len(selected_content.get('skill_ids', [])),
                'selected_content': selected_content,
                'coverage_summary': matching_result.get('coverage_summary', {}),
                'candidate_updated_at': candidate_timestamp,
                'job_updated_at': job_timestamp,
            }
        )
        cached = False
    else:
        selected_content = preview.selected_content
        cached = True

    return preview, selected_content, cached



class CandidateProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CandidateProfile.
    GET /api/candidate/profile/ - Get current user's profile
    PUT /api/candidate/profile/ - Update profile
    """
    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'post', 'options', 'head']
    
    def get_queryset(self):
        return CandidateProfile.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create profile for current user."""
        profile, created = CandidateProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'full_name': self.request.user.username,
            }
        )
        return profile
    
    def list(self, request, *args, **kwargs):
        """Return single profile instead of list."""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Handle POST to /api/candidate/profile/ - treat as update."""
        return self.update(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update profile - works for both PUT on list endpoint and detail endpoint."""
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def upload_resume(self, request):
        """
        Upload resume text and autofill profile using LLM parsing.
        POST /api/candidate/profile/upload_resume/
        Body: {"resume_text": "..."}
        """
        resume_text = request.data.get('resume_text')
        if not resume_text:
            return Response({'error': 'resume_text is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info("Parsing resume with LLM...")
            # Parse resume using LLM
            parsed_data = llm_service.parse_resume(resume_text)
            
            # Get or create profile
            profile = self.get_object()
            
            # Update core profile fields
            personal_info = parsed_data.get('personal_info', {})
            name = _clean_text(personal_info.get('name'))
            if name:
                profile.full_name = name
            phone = _clean_text(personal_info.get('phone'))
            if phone:
                profile.phone = phone
            location = _clean_text(personal_info.get('location'))
            if location:
                profile.location = location

            summary = _clean_text(parsed_data.get('summary'))
            if summary:
                profile.summary = summary

            preferred_roles = _clean_string_list(parsed_data.get('preferred_roles'))
            profile.preferred_roles = preferred_roles

            links = parsed_data.get('links', {}) or {}
            linkedin = _clean_text(links.get('linkedin') or parsed_data.get('linkedin'))
            github = _clean_text(links.get('github') or parsed_data.get('github'))
            if linkedin:
                profile.linkedin = linkedin
            if github:
                profile.github = github

            custom_links_source = links.get('custom_links')
            if not isinstance(custom_links_source, list):
                custom_links_source = parsed_data.get('custom_links', [])
            profile.custom_links = _normalize_entries(custom_links_source)

            sections_updated = {
                'custom_links': len(profile.custom_links),
                'preferred_roles': len(preferred_roles)
            }
            json_sections = ['education', 'experience', 'publications', 'awards', 'extracurricular', 'patents']
            for section in json_sections:
                cleaned_section = _normalize_entries(parsed_data.get(section, []))
                if section == 'experience':
                    normalized_exp = []
                    for entry in cleaned_section:
                        source_list = entry.get('responsibilities')
                        if isinstance(source_list, list):
                            responsibilities = _clean_string_list(source_list)
                        else:
                            alt = entry.get('achievements') if isinstance(entry.get('achievements'), list) else []
                            responsibilities = _clean_string_list(alt)
                        entry['responsibilities'] = responsibilities
                        normalized_exp.append(entry)
                    cleaned_section = normalized_exp
                setattr(profile, section, cleaned_section)
                sections_updated[section] = len(cleaned_section)

            profile.save()
            profile.refresh_from_db()

            # Create or update projects
            projects_created = []
            projects_updated = []
            for index, proj_data in enumerate(parsed_data.get('projects', []), start=1):
                title = _clean_text(proj_data.get('title'))
                if not title:
                    continue
                description = _clean_text(proj_data.get('description') or proj_data.get('summary'))
                achievements = _clean_string_list(
                    proj_data.get('achievements') or proj_data.get('outcomes')
                )
                defaults = {
                    'description': description,
                    'outcomes': achievements,
                    'order': index,
                }
                start_date = _parse_date_string(proj_data.get('start_date'))
                if start_date:
                    defaults['duration_start'] = start_date
                end_date = _parse_date_string(proj_data.get('end_date'))
                if end_date:
                    defaults['duration_end'] = end_date
                project, created = Project.objects.update_or_create(
                    candidate=profile,
                    title=title,
                    defaults=defaults
                )
                if created:
                    projects_created.append(project.title)
                else:
                    projects_updated.append(project.title)
            
            # Create or update skills
            skills_created = []
            skills_updated = []
            for skill_data in parsed_data.get('skills', []):
                name = _clean_text(skill_data.get('name'))
                if not name:
                    continue
                category = (skill_data.get('category') or Skill.Category.TECHNICAL).upper()
                if category not in dict(Skill.Category.choices):
                    category = Skill.Category.TECHNICAL
                skill, _ = Skill.objects.get_or_create(
                    name=name,
                    defaults={'category': category}
                )
                proficiency = (skill_data.get('proficiency_level') or CandidateSkill.ProficiencyLevel.INTERMEDIATE).upper()
                if proficiency not in dict(CandidateSkill.ProficiencyLevel.choices):
                    proficiency = CandidateSkill.ProficiencyLevel.INTERMEDIATE
                defaults = {
                    'proficiency_level': proficiency,
                    'years_of_experience': _to_decimal(skill_data.get('years_of_experience'))
                }
                candidate_skill, created = CandidateSkill.objects.update_or_create(
                    candidate=profile,
                    skill=skill,
                    defaults=defaults
                )
                if created:
                    skills_created.append(skill.name)
                else:
                    skills_updated.append(skill.name)
            
            # Create tools
            tools_created = []
            for tool_data in parsed_data.get('tools', []):
                name = _clean_text(tool_data.get('name'))
                if not name:
                    continue
                category = (tool_data.get('category') or Tool.Category.OTHER).upper()
                if category not in dict(Tool.Category.choices):
                    category = Tool.Category.OTHER
                tool, created = Tool.objects.get_or_create(
                    name=name,
                    defaults={'category': category}
                )
                if created:
                    tools_created.append(tool.name)
            
            logger.info(f"Resume parsed successfully: {len(projects_created)} projects, {len(skills_created)} skills")
            
            return Response({
                'message': 'Resume parsed and profile updated successfully',
                'projects_created': projects_created,
                'projects_updated': projects_updated,
                'skills_created': skills_created,
                'skills_updated': skills_updated,
                'tools_created': tools_created,
                'sections_updated': sections_updated,
                'profile': CandidateProfileSerializer(profile).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Resume parsing failed: {e}")
            return Response({'error': f'Failed to parse resume: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Project management.
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get projects for current user's profile."""
        try:
            profile = CandidateProfile.objects.get(user=self.request.user)
            return Project.objects.filter(candidate=profile)
        except CandidateProfile.DoesNotExist:
            return Project.objects.none()
    
    def perform_create(self, serializer):
        """Create project for current user's profile."""
        profile, created = CandidateProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'full_name': self.request.user.username}
        )
        serializer.save(candidate=profile)


class SkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Skill management (master list).
    """
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    queryset = Skill.objects.all()
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """Get or create a skill by name."""
        name = request.data.get('name')
        category = request.data.get('category', 'TECHNICAL')
        
        if not name:
            return Response({'error': 'Skill name is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        skill, created = Skill.objects.get_or_create(
            name=name,
            defaults={'category': category}
        )
        serializer = self.get_serializer(skill)
        return Response(serializer.data, 
                       status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CandidateSkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CandidateSkill management (user's skills).
    """
    serializer_class = CandidateSkillSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get skills for current user's profile."""
        try:
            profile = CandidateProfile.objects.get(user=self.request.user)
            return CandidateSkill.objects.filter(candidate=profile)
        except CandidateProfile.DoesNotExist:
            return CandidateSkill.objects.none()
    
    def perform_create(self, serializer):
        """Add skill to current user's profile."""
        profile, created = CandidateProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'full_name': self.request.user.username}
        )
        serializer.save(candidate=profile)


class ToolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tool management.
    """
    serializer_class = ToolSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tool.objects.all()


class DomainViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Domain management.
    """
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]
    queryset = Domain.objects.all()


class CandidateApplicationPreviewView(APIView):
    """Return match-strength preview for a candidate applying to a job."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_object_or_404(CandidateProfile, user=request.user)
        job_id = request.data.get('job_id')

        if not job_id:
            return Response({'error': 'job_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(JobDescription, id=job_id)

        if job.status != JobDescription.Status.ACTIVE:
            return Response({'error': 'Job is not accepting applications'}, status=status.HTTP_400_BAD_REQUEST)

        force_refresh_flag = request.data.get('force_refresh')
        force_refresh = False
        if isinstance(force_refresh_flag, bool):
            force_refresh = force_refresh_flag
        elif isinstance(force_refresh_flag, str):
            force_refresh = force_refresh_flag.lower() in {'1', 'true', 'yes'}

        preview, selected_content, cached = _get_or_compute_preview(
            profile,
            job,
            force_refresh=force_refresh
        )

        return Response({
            'job_id': job.id,
            'job_title': job.title,
            'match_strength': preview.match_strength,
            'required_coverage': preview.required_coverage,
            'selected_projects': preview.selected_projects,
            'selected_skills': preview.selected_skills,
            'selected_content': selected_content,
            'coverage_summary': preview.coverage_summary,
            'cached': cached,
            'computed_at': preview.computed_at.isoformat(),
        }, status=status.HTTP_200_OK)


class CandidateApplicationView(APIView):
    """Allow candidates to apply to jobs using snapshots or existing resumes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_object_or_404(CandidateProfile, user=request.user)
        applications = Application.objects.filter(candidate=profile).order_by('-applied_at')
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, application_id=None):
        """Allow candidates to withdraw pending applications."""
        profile = get_object_or_404(CandidateProfile, user=request.user)
        
        if not application_id:
            return Response({'error': 'application_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        application = get_object_or_404(
            Application,
            id=application_id,
            candidate=profile
        )
        
        if application.status != Application.Status.PENDING:
            return Response(
                {'error': 'Only pending applications can be withdrawn'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.delete()
        return Response(
            {'message': 'Application withdrawn successfully'},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        profile = get_object_or_404(CandidateProfile, user=request.user)
        job_id = request.data.get('job_id')
        resume_id = request.data.get('resume_id')

        if not job_id:
            return Response({'error': 'job_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(JobDescription, id=job_id)

        if job.status != JobDescription.Status.ACTIVE:
            return Response({'error': 'Job is not accepting applications'}, status=status.HTTP_400_BAD_REQUEST)

        preview, selected_content, _ = _get_or_compute_preview(profile, job)
        candidate_snapshot = build_candidate_snapshot(profile, selected_content)

        resume_identifier = str(uuid.uuid4())
        pdf_path = ''
        resume_reference = None

        if resume_id:
            resume_reference = GeneratedResume.objects.filter(
                candidate=profile,
                resume_id=resume_id
            ).first()
            if not resume_reference:
                return Response({'error': 'Resume not found'}, status=status.HTTP_404_NOT_FOUND)
            resume_identifier = resume_reference.resume_id
            pdf_path = resume_reference.pdf_path

        # Create application immediately with pending match explanation
        match_explanation = {
            'decision': 'REVIEW',
            'confidence': 0.0,
            'explanation': 'Match analysis in progress...',
            'strengths': [],
            'gaps': [],
        }

        application_defaults = {
            'resume_id': resume_identifier,
            'resume_version': candidate_snapshot,
            'generated_pdf_path': pdf_path,
            'match_explanation': match_explanation,
            'status': Application.Status.PENDING,  # Reset to PENDING on reapplication
        }

        application, created = Application.objects.update_or_create(
            candidate=profile,
            job=job,
            defaults=application_defaults
        )

        # Generate match explanation asynchronously in background
        import threading
        def generate_explanation_async():
            try:
                explanation = llm_service.generate_match_explanation(selected_content)
                # Update application with generated explanation
                Application.objects.filter(id=application.id).update(
                    match_explanation=explanation
                )
                logger.info(f"Match explanation generated for application {application.id}")
            except Exception as exc:
                logger.warning(f"Match explanation generation failed for application {application.id}: {exc}")
                fallback_explanation = {
                    'decision': 'REVIEW',
                    'confidence': 0.0,
                    'explanation': 'Match explanation generation encountered an error.',
                    'strengths': [],
                    'gaps': [],
                    'error': str(exc),
                }
                Application.objects.filter(id=application.id).update(
                    match_explanation=fallback_explanation
                )
        
        thread = threading.Thread(target=generate_explanation_async)
        thread.daemon = True
        thread.start()

        return Response({
            'message': 'Application submitted successfully' if created else 'Application updated successfully',
            'application_id': application.id,
            'job_id': job.id,
            'resume_id': resume_identifier,
            'has_pdf': bool(pdf_path),
            'match_explanation': match_explanation,
            'selected_content': selected_content,
            'match_strength': preview.match_strength,
            'resume_source': 'existing' if resume_reference else 'snapshot',
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
