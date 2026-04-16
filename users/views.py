from rest_framework import generics, permissions
from rest_framework.response import Response
from .serializers import RegisterSerializer, UserProfileSerializer
from .models import User


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    CreateAPIView = 處理新增的 View
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny] # 不論是否登入都可以看到

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/users/me/
    RetrieveUpdateAPIView = 處理讀取與更新
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]  # 需要登入才能看

    def get_object(self):
        """
        複寫 get_object: 不用id，直接回傳"目前登入的使用者"
        這是 /me/ 端點的核心邏輯
        """
        return self.request.user

