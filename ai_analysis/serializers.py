from rest_framework import serializers
from .models import AIAnalysis

class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'id', 'diary_entry', 'summary',
            'suggestions', 'exceeded_nutrients', 'lacking_nutrients',
            'nutrition_score', 'status', 'ai_model_used', 'created_at'
        ]
        read_only_fields = fields