from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    Extends Django's AbstractUser to add role field.
    """
    
    class Role(models.TextChoices):
        CANDIDATE = 'CANDIDATE', 'Candidate'
        RECRUITER = 'RECRUITER', 'Recruiter'
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CANDIDATE,
        help_text="User role: Candidate or Recruiter"
    )
    
    email = models.EmailField(
        unique=True,
        help_text="User's email address (must be unique)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Make email the primary identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'role']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def is_candidate(self):
        """Check if user is a candidate."""
        return self.role == self.Role.CANDIDATE
    
    @property
    def is_recruiter(self):
        """Check if user is a recruiter."""
        return self.role == self.Role.RECRUITER
