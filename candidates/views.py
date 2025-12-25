from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
from llm_service.gemini_service import LLMService
import logging

logger = logging.getLogger(__name__)
llm_service = LLMService()


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
            
            # Update personal info
            personal_info = parsed_data.get('personal_info', {})
            if personal_info.get('name'):
                profile.full_name = personal_info['name']
            if personal_info.get('phone'):
                profile.phone = personal_info['phone']
            profile.save()
            
            # Create projects
            projects_created = []
            for proj_data in parsed_data.get('projects', []):
                project, created = Project.objects.get_or_create(
                    candidate=profile,
                    title=proj_data['title'],
                    defaults={
                        'description': proj_data.get('description', ''),
                        'outcomes': proj_data.get('outcomes', [])
                    }
                )
                if created:
                    projects_created.append(project.title)
            
            # Create skills
            skills_created = []
            for skill_data in parsed_data.get('skills', []):
                skill, _ = Skill.objects.get_or_create(
                    name=skill_data['name'],
                    defaults={'category': skill_data.get('category', 'TECHNICAL')}
                )
                candidate_skill, created = CandidateSkill.objects.get_or_create(
                    candidate=profile,
                    skill=skill,
                    defaults={'proficiency_level': 'INTERMEDIATE'}
                )
                if created:
                    skills_created.append(skill.name)
            
            # Create tools
            tools_created = []
            for tool_data in parsed_data.get('tools', []):
                tool, created = Tool.objects.get_or_create(
                    name=tool_data['name'],
                    defaults={'category': tool_data.get('category', 'FRAMEWORK')}
                )
                if created:
                    tools_created.append(tool.name)
            
            logger.info(f"Resume parsed successfully: {len(projects_created)} projects, {len(skills_created)} skills")
            
            return Response({
                'message': 'Resume parsed and profile updated successfully',
                'projects_created': projects_created,
                'skills_created': skills_created,
                'tools_created': tools_created,
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
