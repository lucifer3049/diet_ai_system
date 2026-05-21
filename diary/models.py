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
    
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', '等待分析'
        PROCESSING = 'processing', '分析中'
        COMPLETED = 'completed', '分析完成'
        FAILED = 'failed', '分析失敗'


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


    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, help_text="AI分析狀態")

    class Meta:
        db_table = 'diary_entries'
        verbose_name = '飲食日記'
        ordering = ['user', '-date', '-meal_type'] # 預設排序:使用者 + 日期(新到舊) + 餐別(早餐->點心)

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.get_meal_type_display()}"
    

class DiaryComponent(models.Model):
    """
    圖片辨識後分解出食物成分
    DiaryEntry對應多個 Component
    """

    diary_entry = models.ForeignKey(DiaryEntry, on_delete=models.CASCADE, related_name='components', help_text="所屬日記", verbose_name="日記所屬")
    food_name = models.CharField(max_length=200, help_text="成分名稱，例如:雞肉絲、白飯", verbose_name="食物名稱")
    portion_description = models.CharField(max_length=200, blank=True, help_text="預估份量", verbose_name="預估份量")
    calories = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="卡路里")
    protein = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="蛋白質")
    fat = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="脂肪")
    saturated_fat = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="飽和脂肪")
    trans_fat = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="反式脂肪")
    carbohydrates = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="碳水化合物")
    sugar = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="糖")
    sodium = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="納")

    class SourceChoices(models.TextChoices):
        AI_VISION = 'ai_vision', 'AI視覺辨識'
        AI_TEXT   = 'ai_text',   'AI文字分析'
        CACHE     = 'cache',     '快取'

    source = models.CharField(
        max_length=20,
        choices=SourceChoices.choices,
        default=SourceChoices.AI_VISION,
    )

    class Meta:
        db_table = 'diary_components'
        verbose_name = '食物成份明細'
        verbose_name_plural = '食物成份明細'

    def __str__(self) -> str:
        return f"{self.food_name} (日記#{self.diary_entry_id})"
