from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FoodViewSet

# Router 自動產生 CRUD 的 URL
# FoodViewSet -> GER / foods/, POST / foods/, GET /food/{id}, PATCH /foods/{id}/, DELETE /foods/{id}/
router = DefaultRouter()
router.register(r'foods', FoodViewSet, basename='food')

urlpatterns = [
    path('', include(router.urls)),
]