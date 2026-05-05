import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from ai_analysis.services.base import NutritionAnalysisResult, DietaryAdviceResult
from diary.models import DiaryEntry
from ai_analysis.models import AIAnalysis

User = get_user_model()

MOCK_NUTRITION = NutritionAnalysisResult(
    calories=550.0, protein=30.0, fat=20.0,
    saturated_fat=5.0, trans_fat=0.1, carbohydrates=60.0,
    sugar=10.0, sodium=800.0,
    food_description="雞腿便當",
    raw_response='{"mock": true}'
)

MOCK_ADVICE = DietaryAdviceResult(
    summary="這餐營養均衡",
    exceeded_nutrients=["鈉"],
    lacking_nutrients=["膳食纖維"],
    next_meal_suggestions=["建議下一餐多攝取蔬菜"],
    nutrition_score=75,
    raw_response='{"mock": true}'
)


@pytest.mark.django_db
class TestDiaryCreateView:
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client, user):
        self.client = authenticated_client
        self.user = user
        self.url = '/api/v1/diary/'

    @patch('diary.views.get_ai_service')
    def test_create_diary_triggers_ai_analysis(self, mock_get_service):
        """新增日記後，AI 分析應自動執行並儲存結果"""
        mock_service = MagicMock()
        mock_service.analyze_food_nutrition.return_value = MOCK_NUTRITION
        mock_service.give_dietary_advice.return_value = MOCK_ADVICE
        mock_service.model_name = 'gpt-4o-mini'
        mock_get_service.return_value = mock_service

        response = self.client.post(self.url, {
            'date': '2026-05-06',
            'meal_type': 'lunch',
            'food_name': '雞腿便當',
            'portion_description': '一個'
        })

        assert response.status_code == 201
        
        diary = DiaryEntry.objects.get(id=response.data['id'])
        assert diary.status == 'completed'
        assert float(diary.calories) == 550.0
        assert float(diary.protein) == 30.0

        analysis = AIAnalysis.objects.get(diary_entry=diary)
        assert analysis.status == 'completed'
        assert analysis.nutrition_score == 75
        assert "鈉" in analysis.exceeded_nutrients

    @patch('diary.views.get_ai_service')
    def test_ai_failure_marks_diary_as_failed(self, mock_get_service):
        """AI 分析失敗時，日記狀態應標記為 failed，不拋出 500"""
        mock_service = MagicMock()
        mock_service.analyze_food_nutrition.side_effect = Exception("API timeout")
        mock_get_service.return_value = mock_service

        response = self.client.post(self.url, {
            'date': '2026-05-06',
            'meal_type': 'lunch',
            'food_name': '牛肉麵'
        })

        # API 應正常回傳 201，不因為 AI 失敗而變成 500
        assert response.status_code == 201
        
        diary = DiaryEntry.objects.get(id=response.data['id'])
        assert diary.status == 'failed'

    @patch('diary.views.get_ai_service')
    def test_food_nutrition_cache_is_used(self, mock_get_service):
        """相同食物第二次新增時，應使用快取而不重新呼叫 AI"""
        from nutrition.models import FoodNutritionCache
        
        # 預先建立快取
        FoodNutritionCache.objects.create(
            food_name='滷肉飯',
            calories=400, protein=15, fat=12,
            saturated_fat=3, trans_fat=0,
            carbohydrates=55, sugar=5, sodium=600,
            food_description='滷肉飯一碗'
        )

        mock_service = MagicMock()
        mock_service.give_dietary_advice.return_value = MOCK_ADVICE
        mock_service.model_name = 'gpt-4o-mini'
        mock_get_service.return_value = mock_service

        self.client.post(self.url, {
            'date': '2026-05-06',
            'meal_type': 'dinner',
            'food_name': '滷肉飯'
        })

        # analyze_food_nutrition 不應被呼叫（使用快取）
        mock_service.analyze_food_nutrition.assert_not_called()
        
        cache = FoodNutritionCache.objects.get(food_name='滷肉飯')
        assert cache.hit_count == 1

    def test_create_diary_requires_authentication(self):
        """未認證的請求應回傳 401"""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.post(self.url, {
            'date': '2026-05-06',
            'meal_type': 'lunch',
            'food_name': '雞腿便當'
        })
        assert response.status_code == 401