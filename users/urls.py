from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, UserProfileView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),  # 註冊
    path('auth/login/', TokenObtainPairView.as_view(), name='login'), # 登入
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'), # 刷新token
    path('users/me/', UserProfileView.as_view(), name='user-profile'), # 使用者
]