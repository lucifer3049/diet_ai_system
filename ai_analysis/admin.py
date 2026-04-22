from django.contrib import admin
from .models import AIAnalysis

@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user', 'diary_entry', 'nutrition_score', 'status', 'ai_model_used', 'created_at']
    list_filter = ['status', 'ai_model_used']
    search_fields = ['user__username']
    readonly_fields = ['prompt_sent', 'raw_response', 'created_at'] # 唯獨的欄位，只能看
