from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiaryEntryViewSet

# DRF 自動產生 RESTful API
router = DefaultRouter()

# 註冊 DiaryEntryViewSet 到 /diary/
router.register('diary', DiaryEntryViewSet, basename='diary')

# 自動生成所有的URL加到Django
urlpatterns = [
    path('', include(router.urls)),
]