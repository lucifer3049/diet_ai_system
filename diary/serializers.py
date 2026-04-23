from rest_framework import serializers
from .models import DiaryEntry


class DiaryEntrySerializer(serializers.ModelSerializer):

    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DiaryEntry
        fields = [
            'id', 'date', 'meal_type', 'meal_type_display',
            'food_name', 'portion_description', 'image', 'remark',
            'calories', 'protein', 'fat', 'saturated_fat',
            'trans_fat', 'carbohydrates', 'sugar', 'sodium',
            'status', 'status_display',
            'created_at',
        ]
        read_only_fields = [
            'id', 'calories', 'protein', 'fat', 'saturated_fat',
            'trans_fat', 'carbohydrates', 'sugar', 'sodium',
            'status', 'created_at',
        ]
