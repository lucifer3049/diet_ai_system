from rest_framework import serializers
from .models import AIAnalysis

class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'id', 'diary_entry', 'summary',
            'suggestions', 'nutrition_score',
            'status', 'ai_model_used', 'created_at'
        ]