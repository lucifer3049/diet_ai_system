from rest_framework import serializers
from .models import Food

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = [
            'id', 'name', 'category',
            'calories_per_100g', 'protein_per_100g',
            'carbs_per_100g', 'fat_per_100g', 'fiber_per_100g',
            'created_at'
        ]

        read_only_fields = ['id', 'created_at']