import logging
from dataclasses import dataclass
from diary.models import DiaryEntry
from ai_analysis.models import AIAnalysis
from ai_analysis.services import get_ai_service

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """服務層回傳的結果，不依賴 Django Model"""
    analysis: AIAnalysis
    is_cached: bool # 是否使用已有的分析結果

class AIAnalysisService:
    """
    AI 飲食分析業務邏輯
    View 不需要放AI業務邏輯
    只需要呼叫這個服務層的方法就好
    """

    def analyze_diary(self, diary_entry: DiaryEntry, provider: str) -> AnalysisResult:
        """
        對每一筆日記進行AI分析
        已有的分析結果則直接回傳，不需要重複呼叫AI
        """

        # 回傳已有的分析結果
        if hasattr(diary_entry, 'ai_analysis'):
            logger.info(f"日誌 {diary_entry.id} 使用快取分析結果")
            return AnalysisResult(
                analysis=diary_entry.ai_analysis,
                is_cached=True
            )
        
        # 業務規則邏輯
        self._validate_diary_ready(diary_entry)

        # 組裝資料(業務邏輯)
        diary_data = self._build_diary_data(diary_entry)
        user_profile = self._build_user_profile(diary_entry.user)
        daily_needs = diary_entry.user.daily_nutrition_needs or {}

        # 呼叫 AI
        service = get_ai_service(provider)
        result = service.give_dietary_advice(diary_data, user_profile, daily_needs)

        # 儲存結果
        analysis = AIAnalysis.objects.create(
            user=diary_entry.user,
            diary_entry=diary_entry,
            prompt_sent=f"飲食建議分析：{diary_entry.food_name}",
            raw_response=result.raw_response,
            summary=result.summary,
            suggestions=result.next_meal_suggestions,
            exceeded_nutrients=result.exceeded_nutrients,
            lacking_nutrients=result.lacking_nutrients,
            nutrition_score=result.nutrition_score,
            status=AIAnalysis.StatusChoices.COMPLETED,
            ai_model_used=f"{provider}:{service.model_name}",
        )

        logger.info(f"日誌 {diary_entry.id} AI 分析完成，score={result.nutrition_score}")

        return AnalysisResult(analysis=analysis, is_cached=False)
    
    def _validate_diary_ready(self, diary_entry: DiaryEntry) -> None:
        """
        驗證日記是否可進行分析
        業務規則集中在這裡，不寫在view
        """

        if diary_entry.status == DiaryEntry.StatusChoices.PENDING:
            raise DiaryNotReadyError("營養成分分析尚未完成，請燒等")
        
        if diary_entry.status == DiaryEntry.StatusChoices.FAILED:
            raise DiaryNotReadyError("日誌的營養成分分析失敗，無法給予建議")
        
    def _build_diary_data(self, diary_entry: DiaryEntry) -> dict:
        """整理需要給AI的資料"""

        return {
            'food_name': diary_entry.food_name,
            'portion_description': diary_entry.portion_description,
            'meal_type': diary_entry.get_meal_type_display(),
            'calories': float(diary_entry.calories or 0),
            'protein': float(diary_entry.protein or 0),
            'fat': float(diary_entry.fat or 0),
            'saturated_fat': float(diary_entry.saturated_fat or 0),
            'trans_fat': float(diary_entry.trans_fat or 0),
            'carbohydrates': float(diary_entry.carbohydrates or 0),
            'sugar': float(diary_entry.sugar or 0),
            'sodium': float(diary_entry.sodium or 0),
        }
    
    def _build_user_profile(self, user) -> dict:
        """整理使用者的資料給AI"""

        return {
            'gender': user.get_gender_display() if user.gender else '未提供',
            'age': user.age,
            'height': float(user.height) if user.height else None,
            'weight': float(user.weight) if user.weight else None,
            'bmi': user.bmi,
            'goal': user.get_goal_display(),
        }

class DiaryNotReadyError(Exception):
    pass

