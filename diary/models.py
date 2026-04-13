from django.db import models
from django.conf import settings
from nutrition.models import Food

class DiaryEntry(models.Model):
    """
    飲食日記(每一筆紀錄)
    一個使用者可以多筆紀錄 (早餐/午餐/晚餐/點心)
    """

    class MealChoices(models.TextChoices):
        BREAKFAST = 'breakfast', '早餐'
        LUNCH = 'lunch', '午餐'
        DINNER = 'dinner', '晚餐'
        SNACK = 'snack', '點心'


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diary_entries', help_text="使用者")
    date = models.DateField(help_text="紀錄日期")
    meal_type = models.CharField(max_length=20, choices=MealChoices.choices, help_text="餐別")
    remark = models.TextField(blank=True, help_text="備註")

    total_calories = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="總熱量 (kcal)")
    total_protein = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="總蛋白質 (g)")
    total_carbs = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="總碳水化合物 (g)")
    total_fat = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="總脂肪 (g)")
    total_fiber = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="總膳食纖維 (g)")

    
    created_at = models.DateTimeField(auto_now_add=True, help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新時間")

    class Meta:
        db_table = 'diary_entries'
        verbose_name = '飲食日記'
        ordering = ['user', '-date', '-meal_type'] # 預設排序:使用者 + 日期(新到舊) + 餐別(早餐->點心)

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.get_meal_type_display()}"
    
    def calculate_totals(self):
        """重新計算日記的營養總和，回存DB"""

        totals = {'calories': 0 , 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0}
        for diary_food in self.diary_foods.all():
            nutrition = diary_food.food.get_nutrition_for_amount(float(diary_food.amount_g))

            for key in totals:
                totals[key] += nutrition[key]

        self.total_calories = totals['calories']
        self.total_protein = totals['protein']
        self.total_carbs = totals['carbs']
        self.total_fat = totals['fat']
        self.total_fiber = totals['fiber']
        self.save(update_fields=['total_calories', 'total_protein', 'total_carbs', 'total_fat', 'total_fiber'])

class DiaryFood(models.Model):
    """
    日記的食物明細
    """

    diary_entry = models.ForeignKey(DiaryEntry, on_delete=models.CASCADE, related_name='diary_foods', help_text="所屬日記")
    food = models.ForeignKey(Food, on_delete=models.CASCADE, help_text="食物") # PROTECT = 食物被日記使用時，不允許刪除食物
    amount_g = models.DecimalField(max_digits=7, decimal_places=2, help_text="食用量 (g)")

    class Meta:
        db_table = 'diary_foods'
        verbose_name = '日記食物明細'
        
    def __str__(self):
        return f"{self.food.name} {self.amount_g}g"
    
