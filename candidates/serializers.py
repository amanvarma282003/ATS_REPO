from rest_framework import serializers
from .models import (
    CandidateProfile,
    Project,
    Skill,
    CandidateSkill,
    Tool,
    ProjectTool,
    Domain
)


class CandidateProfileSerializer(serializers.ModelSerializer):
    """Serializer for CandidateProfile model."""
    email = serializers.EmailField(source='user.email', read_only=True)
    projects = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateProfile
        fields = [
            'id', 'email', 'full_name', 'phone', 'location', 'preferred_roles',
            'summary', 'linkedin', 'github', 
            'education', 'experience', 'publications', 'awards', 'extracurricular',
            'patents', 'custom_links', 'projects',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_projects(self, obj):
        queryset = obj.projects.all().order_by('order', '-duration_end', '-created_at')
        return ProjectSerializer(queryset, many=True).data


class ToolSerializer(serializers.ModelSerializer):
    """Serializer for Tool model."""
    
    class Meta:
        model = Tool
        fields = ['id', 'name', 'category']
        read_only_fields = ['id']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model."""
    tools = ToolSerializer(many=True, read_only=True, source='project_tools.tool')
    tool_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'duration_start', 'duration_end', 
                  'outcomes', 'order', 'tools', 'tool_ids', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        tool_ids = validated_data.pop('tool_ids', [])
        project = Project.objects.create(**validated_data)
        
        # Create ProjectTool relationships
        for tool_id in tool_ids:
            try:
                tool = Tool.objects.get(id=tool_id)
                ProjectTool.objects.create(project=project, tool=tool)
            except Tool.DoesNotExist:
                pass
        
        return project
    
    def update(self, instance, validated_data):
        tool_ids = validated_data.pop('tool_ids', None)
        
        # Update project fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tools if provided
        if tool_ids is not None:
            instance.project_tools.all().delete()
            for tool_id in tool_ids:
                try:
                    tool = Tool.objects.get(id=tool_id)
                    ProjectTool.objects.create(project=instance, tool=tool)
                except Tool.DoesNotExist:
                    pass
        
        return instance


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model."""
    
    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'is_verified']
        read_only_fields = ['id']


class CandidateSkillSerializer(serializers.ModelSerializer):
    """Serializer for CandidateSkill model."""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_category = serializers.CharField(source='skill.category', read_only=True)
    
    class Meta:
        model = CandidateSkill
        fields = ['id', 'skill', 'skill_name', 'skill_category', 'proficiency_level', 
                  'years_of_experience', 'acquired_from_project', 'created_at']
        read_only_fields = ['id', 'created_at']


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model."""
    
    class Meta:
        model = Domain
        fields = ['id', 'name', 'parent_domain']
        read_only_fields = ['id']
