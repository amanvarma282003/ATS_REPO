from django.urls import path
from .views import GenerateResumeView, DownloadResumeView, ResumeHistoryView

app_name = 'resume_engine'

urlpatterns = [
    path('generate/', GenerateResumeView.as_view(), name='generate'),
    path('download/<str:resume_id>/', DownloadResumeView.as_view(), name='download'),
    path('history/', ResumeHistoryView.as_view(), name='history'),
]
