from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'goal', 'height', 'weight', 'is_staff']
    list_filter = ['goal', 'is_staff', 'is_active']
    search_fields = ['username', 'email']
    
    fieldsets = UserAdmin.fieldsets + (
        ('健康資料', {
            'fields': ('height', 'weight', 'birth_date', 'goal',  'preferred_ai_provider')
        }),
    )


