from django.db import models
from django.conf import settings


class DiaryEntry(models.Model):
    """
    飲食日記
    使用者只需要輸入食物名稱跟時段
    AI 負責分析營養素
    """

    class MealChoices(models.TextChoices):
        BREAKFAST = 'breakfast', '早餐'
        LUNCH = 'lunch', '午餐'
        DINNER = 'dinner', '晚餐'
        SNACK = 'snack', '點心'


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diary_entries', help_text="使用者")
    date = models.DateField(help_text="紀錄日期")
    meal_type = models.CharField(max_length=20, choices=MealChoices.choices, help_text="餐別")

    food_name = models.CharField(max_length=200, help_text="食物名稱，例如:雞腿便當、綠茶")
    portion_description = models.CharField(max_length=200, blank=True, help_text="分量描述，例如:一碗、半碗、一杯")
    image = models.ImageField(upload_to='diary_images/%Y/%m', null=True, blank=True, help_text="食物照片(AI辨識使用)")

    # AI 分析後自動填入的營養素
    calories = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="AI分析熱量 (kcal)")
    protein = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析蛋白質 (g)")
    fat = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析脂肪 (g)")
    saturated_fat = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析飽和脂肪 (g)")
    trans_fat = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析反式脂肪 (g)")
    carbohydrates = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析碳水化合物 (g)")
    sugar = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="AI分析糖 (g)")
    sodium = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="AI分析納 (g)")

    
    created_at = models.DateTimeField(auto_now_add=True, help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新時間")
    remark = models.TextField(blank=True, help_text="備註")


    class StatusChoices(models.TextChoices):
        PENDING = 'pending', '等待分析'
        COMPLETED = 'completed', '分析完成'
        FAILED = 'failed', '分析失敗'


    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, help_text="AI分析狀態")

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

