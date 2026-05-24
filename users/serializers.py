from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password


def _mask_key(key: str | None) -> str | None:
    """只顯示後 6 碼，保護 API key 安全"""
    if not key:
        return None
    return f"...{key[-6:]}" if len(key) > 6 else "...***"

class RegisterSerializer(serializers.ModelSerializer):
    """
    註冊用 Serializer
    password 額外處理: 驗證強度，加密存入
    """
    # write_only= 只接受輸入，不出現回應JSON中
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm')

    def validate(self, data):
        """validate = 跨欄位驗證，確認密碼一致"""

        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "密碼不一致"})
        
        return data
    
    def create(self, validated_data):
        """建立User"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    """
    使用者個人資料 Serializer
    bmi 是 @property，用 read_only讀取
    """
    bmi = serializers.FloatField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    daily_nutrition_needs = serializers.DictField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'gender', 'height', 'weight', 'birth_date',  
            'goal', 'bmi', 'age', 'daily_nutrition_needs',
            'preferred_ai_provider',
            'created_at'
        ]
        read_only_fields = ['id', 'username', 'created_at']

class UserAISettingsSerializer(serializers.ModelSerializer):
    """GET 用：回傳設定，API key 遮罩顯示"""
    openai_api_key = serializers.SerializerMethodField()
    gemini_api_key = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'preferred_ai_provider',
            'preferred_openai_model',
            'preferred_gemini_model',
            'openai_api_key',
            'gemini_api_key',
        ]

    def get_openai_api_key(self, obj) -> str | None:
        return _mask_key(obj.openai_api_key)

    def get_gemini_api_key(self, obj) -> str | None:
        return _mask_key(obj.gemini_api_key)

class UserAISettingsUpdateSerializer(serializers.ModelSerializer):
    """PATCH 用：接受明文 key 寫入（寫入時由 EncryptedCharField 自動加密）"""
    openai_api_key = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, write_only=True
    )
    gemini_api_key = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, write_only=True
    )

    class Meta:
        model = User
        fields = [
            'preferred_ai_provider',
            'preferred_openai_model',
            'preferred_gemini_model',
            'openai_api_key',
            'gemini_api_key',
        ]

    def validate_openai_api_key(self, value):
        if value and not value.startswith('sk-'):
            raise serializers.ValidationError("OpenAI API key 格式錯誤，應以 'sk-' 開頭")
        return value or None

    def validate_gemini_api_key(self, value):
        if value and len(value) < 20:
            raise serializers.ValidationError("Gemini API key 長度不足")
        return value or None
