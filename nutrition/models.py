from django.db import models

class Food(models.Model):
    """
    食物資料庫
    共用資料，不屬於任何一位使用者
    """

    class CategoryChoices(models.TextChoices):
        GRAIN = 'grain', '主食/穀類'
        PROTEIN = 'protein', '蛋白質'
        VEGETABLE = 'vegetable', '蔬菜'
        FRUIT = 'fruit', '水果'
        DAIRY = 'dairy', '乳製品'
        FAT = 'fat', '油脂'
        BEVERAGE = 'beverage', '飲料'
        OTHER = 'other', '其他'


    name = models.CharField(max_length=100, help_text="食物名稱")
    category = models.CharField(max_length=20, choices=CategoryChoices.choices, default=CategoryChoices.OTHER, help_text="食物類別")

    # 營養成份 (每100g)
    calories_per_100g = models.DecimalField(max_digits=7, decimal_places=2, help_text="熱量 (g / 100g)")
    protein_per_100g = models.DecimalField(max_digits=6, decimal_places=2, help_text="蛋白質 (g / 100g)")
    carbs_per_100g = models.DecimalField(max_digits=6, decimal_places=2, help_text="碳水化合物 (g / 100g)")
    fat_per_100g = models.DecimalField(max_digits=6, decimal_places=2, help_text="脂肪 (g / 100g)")
    fiber_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="膳食纖維 (g / 100g)")

    food_image = models.ImageField(upload_to='foods/', null=True, blank=True, help_text="食物圖片 (AI 圖片辨識用)")

    created_at = models.DateTimeField(auto_now_add=True, help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新時間")

    class Meta:
        db_table = 'foods'
        verbose_name = '食物資料庫'
        ordering = ['name'] # 排序:使用名稱排序

    def __str__(self):
        return f"{self.name} ({self.calories_per_100g} kcal / 100g)"
    
    def get_nutrition_for_amount(self, amount_g: float) -> dict:
        """計算指定克數的營養"""

        ratio = amount_g / 100
        return {
            'calories': round(float(self.calories_per_100g) * ratio, 1),
            'protein': round(float(self.protein_per_100g) * ratio, 1),
            'carbs': round(float(self.carbs_per_100g) * ratio, 1),
            'fat': round(float(self.fat_per_100g) * ratio, 1),
            'fiber': round(float(self.fiber_per_100g) * ratio, 1)
        }
    






    
