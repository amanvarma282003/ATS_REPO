from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CandidateProfileViewSet,
    ProjectViewSet,
    SkillViewSet,
    CandidateSkillViewSet,
    ToolViewSet,
    DomainViewSet,
    CandidateApplicationView,
    CandidateApplicationPreviewView
)

app_name = 'candidates'

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'skills', SkillViewSet, basename='skills')
router.register(r'my-skills', CandidateSkillViewSet, basename='my-skills')
router.register(r'tools', ToolViewSet, basename='tools')
router.register(r'domains', DomainViewSet, basename='domains')

# Custom profile endpoint that supports GET and PUT without ID
profile_list = CandidateProfileViewSet.as_view({
    'get': 'list',
    'put': 'update',
    'post': 'create'
})

urlpatterns = [
    path('profile/', profile_list, name='profile'),
    path('profile/upload_resume/', 
         CandidateProfileViewSet.as_view({'post': 'upload_resume'}), 
         name='profile-upload-resume'),
    path('applications/preview/', CandidateApplicationPreviewView.as_view(), name='applications-preview'),
    path('applications/', CandidateApplicationView.as_view(), name='applications'),
    path('', include(router.urls)),
]
