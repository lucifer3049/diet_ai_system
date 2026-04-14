from django.db import models
from django.conf import settings
from diary.models import DiaryEntry

class AIAnalysis(models.Model):
    """ AI 分析結果 """


    class StatusChoices(models.TextChoices):
        PENDING = 'pending', '待分析'
        PROCESSING = 'processing', '分析中'
        COMPLETED = 'completed', '完成'
        FAILED = 'failed', '失敗'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_analyses', help_text="使用者")

    diary_entry = models.OneToOneField(DiaryEntry, on_delete=models.CASCADE, related_name='ai_analysis', help_text="一筆紀錄只對應一份 AI 分析結果")

    prompt_sent = models.TextField(help_text="發送給AI的提示詞")
    raw_response = models.TextField(help_text="AI原始回應")

    summary = models.TextField(help_text="AI 分析結果")
    suggestions = models.JSONField(default=list, help_text="AI 分析建議")
    nutrition_score = models.IntegerField(null=True, blank=True, help_text="營養評分 1-100")

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, help_text="狀態")
    ai_model_used = models.CharField(max_length=50, help_text="使用的 AI 模型(gpt-4o / gemini-pro)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_analyses'
        verbose_name = 'AI 分析結果'

    def __str__(self):
        return f"AI分析 - {self.diary_entry} ({self.status})"
    


