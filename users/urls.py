from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # 內建API
from drf_spectacular.utils import extend_schema
from .views import RegisterView, UserProfileView


# 用 extend_schema 補充 simplejwt的文件說明
TokenObtainPairView = extend_schema(
    tags=["認證"],
    summary="登入 (取得 JWT Token)",
    description="輸入帳密，取的 access token 和 refresh token。access token 有效期限 5 分鐘。"
)(TokenObtainPairView)

TokenRefreshView = extend_schema(
    tags=["認證"],
    summary="刷新 Access Token",
    description="用 refresh token 取的新的 access token，無須重新登入。"
)(TokenRefreshView)

urlpatterns = [

    # 認證
    path('auth/register/', RegisterView.as_view(), name='register'),  # 註冊
    path('auth/login/', TokenObtainPairView.as_view(), name='login'), # 登入
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'), # 刷新token

    # 使用者資料
    path('users/me/', UserProfileView.as_view(), name='user-profile'), # 使用者
]