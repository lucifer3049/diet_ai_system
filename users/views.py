from rest_framework import generics, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .serializers import RegisterSerializer, UserProfileSerializer
from .models import User

@extend_schema(tags=['認證'])
class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    CreateAPIView: 驗證 serializer，存使用者帳密，回傳response
    """

    # 操作 Model會用哪個serializer處理資料
    queryset = User.objects.all()  
    serializer_class = RegisterSerializer


    permission_classes = [permissions.AllowAny] # 不論是否登入都可以看到
    
    # API文件
    @extend_schema(
        summary="使用者註冊",
        description="建立新帳號。username 必須唯一，密碼至少 8 字元。",
        examples=[
            OpenApiExample(
                name="基本範例",
                value={
                    "username": "john_doe",
                    "email": "john@example.com",
                    "password": "Pass123!",
                    "password_confirm": "Pass123!",
                },
                request_only=True, # 顯示在 Request 
            )
        ],
        # Swagger 會顯示告訴要怎麼傳 request 成功的時候
        responses={
            201: OpenApiResponse(
                response=RegisterSerializer,
                description="註冊成功",
                examples=[
                    OpenApiExample(
                        name="成功回應",
                        value={
                            "username": "john_doe",
                            "email": "admin@example.com",
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="資料驗證失敗 (帳號重複或密碼不符)")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
@extend_schema(tags=['使用者'])
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/users/me/
    RetrieveUpdateAPIView = 處理讀取與更新
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]  # 需要登入才能看

    @extend_schema(
            summary="取得個人資料",
            description="取得目前登入使用者的完整資料，包含BMI計算結果",
    )

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
            summary="更新個人資料",
            description="更新身高、體重、飲食目標等資料。只需傳入要更新的欄位。"
    )

    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        """
        複寫 get_object: 不用id，直接回傳"目前登入的使用者"
        這是 /me/ 端點的核心邏輯
        """
        return self.request.user

