from django.db import models
from django.conf import settings


class CandidateProfile(models.Model):
    """
    Candidate profile - the source of truth for candidate data.
    Resume PDFs are derived artifacts, not primary data.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidate_profile'
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    preferred_roles = models.JSONField(
        default=list,
        help_text="List of preferred job roles"
    )
    
    # Extended Profile Fields
    summary = models.TextField(
        blank=True,
        help_text="Professional summary (2-3 sentences)"
    )
    linkedin = models.URLField(
        max_length=500,
        blank=True,
        help_text="LinkedIn profile URL"
    )
    github = models.URLField(
        max_length=500,
        blank=True,
        help_text="GitHub profile URL"
    )
    
    # Structured sections stored as JSON
    education = models.JSONField(
        default=list,
        help_text="List of education entries: [{degree, institution, start_year, end_year, cgpa}]"
    )
    experience = models.JSONField(
        default=list,
        help_text="List of work experiences: [{company, role, start_date, end_date, responsibilities: []}]"
    )
    publications = models.JSONField(
        default=list,
        help_text="List of publications: [{title, venue, date, doi, description}]"
    )
    awards = models.JSONField(
        default=list,
        help_text="List of awards/achievements: [{title, organization, level, date}]"
    )
    extracurricular = models.JSONField(
        default=list,
        help_text="List of extracurricular activities: [{role, organization, location, description}]"
    )
    patents = models.JSONField(
        default=list,
        help_text="List of patents: [{title, patent_number, filing_date, grant_date, description, inventors}]"
    )
    custom_links = models.JSONField(
        default=list,
        help_text="List of custom links: [{label, url, description}]"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_profiles'
        verbose_name = 'Candidate Profile'
        verbose_name_plural = 'Candidate Profiles'
    
    def __str__(self):
        return f"{self.full_name} ({self.user.email})"


class Project(models.Model):
    """
    Projects completed by candidate.
    Used as evidence in knowledge graph.
    """
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    duration_start = models.DateField(null=True, blank=True)
    duration_end = models.DateField(null=True, blank=True)
    outcomes = models.JSONField(
        default=list,
        help_text="List of measurable achievements/metrics"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (for sorting)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        ordering = ['order', '-duration_end', '-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
    
    def __str__(self):
        return f"{self.title} - {self.candidate.full_name}"


class Skill(models.Model):
    """
    Master list of skills.
    Linked to candidates via CandidateSkill through table.
    """
    
    class Category(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical'
        SOFT = 'SOFT', 'Soft Skill'
        DOMAIN = 'DOMAIN', 'Domain Knowledge'
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.TECHNICAL
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this skill is verified/official"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'skills'
        ordering = ['name']
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class CandidateSkill(models.Model):
    """
    Many-to-many relationship between candidates and skills.
    Includes proficiency and experience metadata.
    """
    
    class ProficiencyLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', 'Beginner'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
        EXPERT = 'EXPERT', 'Expert'
    
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='candidate_skills'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='candidate_skills'
    )
    proficiency_level = models.CharField(
        max_length=12,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE
    )
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )
    acquired_from_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skills_acquired',
        help_text="Project where this skill was used/acquired"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'candidate_skills'
        unique_together = ['candidate', 'skill']
        verbose_name = 'Candidate Skill'
        verbose_name_plural = 'Candidate Skills'
    
    def __str__(self):
        return f"{self.candidate.full_name} - {self.skill.name} ({self.proficiency_level})"


class Tool(models.Model):
    """
    Tools, technologies, frameworks, platforms used in projects.
    """
    
    class Category(models.TextChoices):
        LANGUAGE = 'LANGUAGE', 'Programming Language'
        FRAMEWORK = 'FRAMEWORK', 'Framework'
        PLATFORM = 'PLATFORM', 'Platform'
        OTHER = 'OTHER', 'Other'
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.OTHER
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tools'
        ordering = ['name']
        verbose_name = 'Tool'
        verbose_name_plural = 'Tools'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class ProjectTool(models.Model):
    """
    Many-to-many relationship between projects and tools.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_tools'
    )
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name='project_tools'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'project_tools'
        unique_together = ['project', 'tool']
        verbose_name = 'Project Tool'
        verbose_name_plural = 'Project Tools'
    
    def __str__(self):
        return f"{self.project.title} - {self.tool.name}"


class Domain(models.Model):
    """
    Broader knowledge domains (e.g., Machine Learning, Web Development).
    Can have hierarchical structure with parent domains.
    """
    name = models.CharField(max_length=100, unique=True)
    parent_domain = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_domains'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'domains'
        ordering = ['name']
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
    
    def __str__(self):
        if self.parent_domain:
            return f"{self.parent_domain.name} > {self.name}"
        return self.name
