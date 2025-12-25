from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobDescriptionViewSet,
    ApplicationViewSet,
    RecruiterFeedbackViewSet
)

app_name = 'recruiters'

router = DefaultRouter()
router.register(r'jobs', JobDescriptionViewSet, basename='jobs')
router.register(r'applications', ApplicationViewSet, basename='applications')
router.register(r'feedback', RecruiterFeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
]
