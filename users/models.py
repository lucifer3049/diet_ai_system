from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    建立Django內建 User
    繼承 AbstractUser = 保留內建功能 (登入/權限) + 加自己的欄位
    """

    class GenderChoices(models.TextChoices):
        MALE = 'male', '男性'
        FEMALE = 'female', '女性'
        OTHER = 'other', '其他'

    class GoalChoices(models.TextChoices):
        LOSE_WEIGHT = 'lose_weight', '減重'
        MAINTAIN = 'maintain', '維持體重'
        GAIN_MUSCLE = 'gain_muscle', '增肌'

    class AIProviderChoices(models.TextChoices):
        # 使用者選擇自己喜歡的AI模型
        OPENAI = 'openai', 'OpenAI GPT'
        GEMINI = 'gemini', 'Google Gemini'

    class GoalChoices(models.TextChoices):
        LOSE_WEIGHT = 'lose_weight', '減重'
        MAINTAIN = 'maintain', '維持體重'
        GAIN_MUSCLE = 'gain_muscle', '增肌'


    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="身高 (cm)")
    weight = models.DecimalField(max_digits=5,decimal_places=2, null=True, blank=True, help_text="體重 (kg)")
    birth_date = models.DateField(null=True, blank=True, help_text="出生日期")
    goal = models.CharField(max_length=20, choices=GoalChoices.choices, default=GoalChoices.MAINTAIN, help_text="目標")
    daily_calorie_target = models.IntegerField(null=True, blank=True, help_text="每日目標熱量 (kcal)")

    preferred_ai_provider = models.CharField(
        max_length=20, 
        choices=AIProviderChoices.choices, 
        default=AIProviderChoices.OPENAI, 
        help_text="偏好的AI模型提供者"
    )

    # 時間記錄
    created_at = models.DateTimeField(auto_now_add=True, help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新時間")

    class Meta:
        db_table = 'users' # 資料表名稱
        verbose_name = '使用者' # 管理者介面顯示名稱

    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def bmi(self) -> float | None:
        """"計算BMI，暫存資料不存入資料庫，類似Odoo的compute"""
        if self.height and self.weight:
            height_m = float(self.height) / 100 
            return round(float(self.weight) / (height_m ** 2), 1)
        return None
    
    @property
    def age(self) -> int | None:
        """根據生日計算年齡"""
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
    
    @property
    def daily_nutrition_needs(self) -> dict | None:
        """
        根據性別、年齡、身高、體重、目標
        計算每日建議營養素需求
        使用 Harris-Benedict 公式計算基礎代謝率 (BMR)
        """

        if not all([self.gender, self.height, self.weight, self.birth_date]):
            return None
        
        height = float(self.height)
        weight = float(self.weight)
        age = self.age

        # Harris-Benedict 公式計算 BMR (基礎代謝率)
        if self.gender == 'male':
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
        
        # 根據活動水平調整TDEE，假設是輕度活動
        tdee = bmr * 1.375

        # 根據目標調整熱量
        if self.goal == 'lose_weight':
            calories = tdee - 500 # 每天最少 500 大卡
        elif self.goal == 'gain_muscle':
            calories = tdee + 300 # 每天最多500大卡
        else:
            calories = tdee
        
        calories = round(calories)

        return {
            'calories': calories,
            'protein': round(weight * 1.6),                 # 每公斤體重 1.6g 蛋白質
            'fat': round(calories * 0.25 / 9),              # 每公升體重 0.25g 脂肪     
            'saturated_fat': round(calories * 0.07 / 9),    # 每公升體重 0.07g 飽和脂肪
            'carbohydrates': round(calories * 0.5 / 4),     # 每公升體重 0.5g 碳水化合物
            'sugar': round(calories * 0.1 / 4),             # 每公升體重 0.1g 糖分
            'sodium': 2300,                                # WHO建議每天鈉攝取量不超過 2300mg
        }


        