from django.urls import path
from .views import (
    GenerateResumeView,
    DownloadResumeView,
    ResumeHistoryView,
    ResumeLabelPreviewView,
)

app_name = 'resume_engine'

urlpatterns = [
    path('generate/', GenerateResumeView.as_view(), name='generate'),
    path('download/<str:resume_id>/', DownloadResumeView.as_view(), name='download'),
    path('history/', ResumeHistoryView.as_view(), name='history'),
    path('label/', ResumeLabelPreviewView.as_view(), name='label'),
]
