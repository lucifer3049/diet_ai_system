from django.contrib import admin
from .models import Food, FoodNutritionCache

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g', 'fiber_per_100g']
    list_filter = ['category']
    search_fields = ['name']



@admin.register(FoodNutritionCache)
class FoodNutritionCacheAdmin(admin.ModelAdmin):
    list_display = ['food_name', 'calories', 'protein', 'ai_model_used', 'hit_count', 'created_at']
    search_fields = ['food_name']
    readonly_fields = ['hit_count', 'created_at', 'updated_at']