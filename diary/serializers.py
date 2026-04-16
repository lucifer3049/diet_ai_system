from rest_framework import serializers
from .models import DiaryEntry, DiaryFood
from nutrition.serializers import FoodSerializer

class DiaryFoodSerializer(serializers.ModelSerializer):
    """日記的每項食物的排序"""

    food_detail = FoodSerializer(source='food', read_only=True)

    class Meta:
        model = DiaryFood
        fields = ['id', 'food', 'food_detail', 'amount_g']

class DiaryEntrySerializer(serializers.ModelSerializer):
    """
    食物日記主體排序
    diary_foods = 巢狀排序 (一筆日記包含多項食物明細)
    """

    diary_foods = DiaryFoodSerializer(many=True, read_only=True)
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = DiaryEntry
        fields = [
            'id', 'date', 'meal_type', 'meal_type_display',
            'notes', 'diary_foods',
            'total_calories', 'total_protein', 'total_cards', 'total_fat',
            'created_at'
        ]

        read_only_fields = [
            'id', 'total_calories', 'total_protein', 'total_carbs', 'total_fat', 'created_at'
        ]

class AddFoodToDiarySerializer(serializers.Serializer):
    """新增食物到日記的 Serializer"""

    food_id = serializers.IntegerField()
    amount_g = serializers.DecimalField(max_digits=7, decimal_places=2)