from django.contrib import admin
from .models import DiaryEntry, DiaryFood

class DiaryFoodInline(admin.TabularInline):
    """
    Inline = 在 DiaryEntry 的表單中顯示關聯的 DiaryFood
    TabularInline = 表格形式顯示
    """

    model = DiaryFood
    extra = 0 # 預設不顯示空白

@admin.register(DiaryEntry)
class DiaryEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'meal_type', 'total_calories', 'total_protein']
    list_filter = ['meal_type', 'date']
    search_fields = ['user__username']
    inlines = [DiaryFoodInline] # 在 DiaryEntry 顯示 DiaryFood 明細