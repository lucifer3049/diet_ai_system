from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    建立Django內建 User
    繼承 AbstractUser = 保留內建功能 (登入/權限) + 加自己的欄位
    """
    class GoalChoices(models.TextChoices):
        LOSE_WEIGHT = 'lose_weight', '減重'
        MAINTAIN = 'maintain', '維持體重'
        GAIN_MUSCLE = 'gain_muscle', '增肌'


    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="身高 (cm)")
    weight = models.DecimalField(max_digits=5,decimal_places=2, null=True, blank=True, help_text="體重 (kg)")
    birth_date = models.DateField(null=True, blank=True, help_text="出生日期")
    goal = models.CharField(max_length=20, choices=GoalChoices.choices, default=GoalChoices.MAINTAIN, help_text="目標")
    daily_calorie_target = models.IntegerField(null=True, blank=True, help_text="每日目標熱量 (kcal)")

    # 時間記錄
    created_at = models.DateTimeField(auto_now_add=True, help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新時間")

    class Meta:
        db_table = 'users' # 資料表名稱
        verbose_name = '使用者' # 管理者介面顯示名稱

    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def bmi(self):
        """"計算BMI"""
        if self.height and self.weight:
            height_m = float(self.height) / 100 
            return round(float(self.weight) / (height_m ** 2), 1)
        return None