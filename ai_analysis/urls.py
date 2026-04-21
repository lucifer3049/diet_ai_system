from django.urls import path
from .views import AnalyzeDiaryView, MyAnalysisListView

urlpatterns = [
    path('ai/analyze/<int:diary_id>/', AnalyzeDiaryView.as_view(), name='analyze-diary'),
    path('ai/my-analyses/', MyAnalysisListView.as_view(), name='my-analyses'),
]