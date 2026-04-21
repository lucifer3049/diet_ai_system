from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password

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
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'height', 'weight', 'birth_date',
            'goal', 'daily_calorie_target', 'bmi',
            'preferred_ai_provider', 
            'created_at'
        ]
        read_only_fields = ['id', 'username', 'created_at']
      