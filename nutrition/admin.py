from django.contrib import admin
from .models import Food

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g', 'fiber_per_100g']
    list_filter = ['category']
    search_fields = ['name']


