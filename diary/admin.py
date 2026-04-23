from django.contrib import admin
from .models import DiaryEntry


@admin.register(DiaryEntry)
class DiaryEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'meal_type', 'calories', 'protein', 'fat', 'saturated_fat', 'trans_fat', 'carbohydrates', 'sugar', 'sodium', 'status']
    list_filter = ['meal_type', 'date']
    search_fields = ['user__username', 'food_name']
    readonly_fields = ['calories', 'protein', 'fat', 'saturated_fat', 'trans_fat', 'carbohydrates', 'sugar', 'sodium', 'status']