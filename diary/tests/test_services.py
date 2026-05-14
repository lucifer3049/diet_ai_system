"""
測試 DiaryService 的業務邏輯：
  - 快取命中時不呼叫 AI
  - 快取未命中時呼叫 AI 並寫入 DB
  - 快取命中數計數正確更新
  - AI 分析完整流程(nutrition + advice + AIAnalysis 建立)
  - 例外時不建立不完整的資料
"""
import pytest
from unittest.mock import patch, MagicMock, call
from diary.services import DiaryService
from diary.models import DiaryEntry
from nutrition.models import FoodNutritionCache
from ai_analysis.models import AIAnalysis
from ai_analysis.services.base import NutritionAnalysisResult, DietaryAdviceResult
from diary.tests.factories import DiaryEntryFactory
from nutrition.tests.factories import FoodNutritionCacheFactory
from users.tests.factories import UserFactory


def make_mock_nutrition(**kwargs) -> NutritionAnalysisResult:
    defaults = dict(
        calories=550.0, protein=30.0, fat=20.0,
        saturated_fat=5.0, trans_fat=0.1, carbohydrates=60.0,
        sugar=10.0, sodium=800.0,
        food_description='雞腿便當一個',
        raw_response='{"mock": true}',
    )
    return NutritionAnalysisResult(**{**defaults, **kwargs})


def make_mock_advice(**kwargs) -> DietaryAdviceResult:
    defaults = dict(
        summary='這餐營養均衡',
        exceeded_nutrients=['鈉'],
        lacking_nutrients=['膳食纖維'],
        next_meal_suggestions=['多吃蔬菜'],
        nutrition_score=75,
        raw_response='{"mock": true}',
    )
    return DietaryAdviceResult(**{**defaults, **kwargs})


@pytest.mark.django_db
class TestGetNutritionFromCacheOrAI:

    def test_returns_cached_result_when_db_cache_exists(self):
        """DB 有快取時，直接回傳，不呼叫 AI"""
        cache = FoodNutritionCacheFactory(food_name='白米飯', calories=130)
        mock_service = MagicMock()

        result = DiaryService.get_nutrition_from_cache_or_ai('白米飯', '', mock_service)

        mock_service.analyze_food_nutrition.assert_not_called()
        assert float(result.calories) == 130

    def test_increments_hit_count_on_cache_hit(self):
        """快取命中時，hit_count 應 +1"""
        cache = FoodNutritionCacheFactory(food_name='滷肉飯', hit_count=5)
        mock_service = MagicMock()

        DiaryService.get_nutrition_from_cache_or_ai('滷肉飯', '', mock_service)

        cache.refresh_from_db()
        assert cache.hit_count == 6

    def test_calls_ai_when_no_cache(self):
        """無快取時，呼叫 AI 並寫入 DB"""
        mock_service = MagicMock()
        mock_service.model_name = 'gpt-4o-mini'
        mock_service.analyze_food_nutrition.return_value = make_mock_nutrition()

        DiaryService.get_nutrition_from_cache_or_ai('新食物', '一份', mock_service)

        mock_service.analyze_food_nutrition.assert_called_once_with(
            food_name='新食物',
            portion_description='一份',
        )

    def test_saves_ai_result_to_db_cache(self):
        """AI 分析結果應寫入 FoodNutritionCache"""
        mock_service = MagicMock()
        mock_service.model_name = 'gpt-4o-mini'
        mock_service.analyze_food_nutrition.return_value = make_mock_nutrition(
            calories=600.0
        )

        DiaryService.get_nutrition_from_cache_or_ai('牛肉麵', '', mock_service)

        assert FoodNutritionCache.objects.filter(food_name='牛肉麵').exists()
        saved = FoodNutritionCache.objects.get(food_name='牛肉麵')
        assert float(saved.calories) == 600.0

    def test_cache_lookup_case_insensitive(self):
        """大小寫不同的食物名稱應命中同一筆快取"""
        FoodNutritionCacheFactory(food_name='雞腿便當')
        mock_service = MagicMock()

        # 大寫不同也應命中
        DiaryService.get_nutrition_from_cache_or_ai('雞腿便當', '', mock_service)

        mock_service.analyze_food_nutrition.assert_not_called()

    def test_does_not_create_duplicate_cache(self):
        """同一食物不應建立兩筆快取"""
        mock_service = MagicMock()
        mock_service.model_name = 'gpt-4o-mini'
        mock_service.analyze_food_nutrition.return_value = make_mock_nutrition()

        DiaryService.get_nutrition_from_cache_or_ai('壽司', '', mock_service)
        DiaryService.get_nutrition_from_cache_or_ai('壽司', '', mock_service)

        # 第二次應命中快取，DB 只有一筆
        assert FoodNutritionCache.objects.filter(food_name='壽司').count() == 1


@pytest.mark.django_db
class TestSaveNutritionToDiary:

    def test_saves_all_nutrition_fields(self, user):
        diary = DiaryEntryFactory(user=user)
        nutrition = make_mock_nutrition()

        DiaryService.save_nutrition_to_diary(diary, nutrition)

        diary.refresh_from_db()
        assert float(diary.calories) == 550.0
        assert float(diary.protein) == 30.0
        assert float(diary.fat) == 20.0
        assert float(diary.sodium) == 800.0

    def test_sets_status_to_completed(self, user):
        diary = DiaryEntryFactory(user=user)
        DiaryService.save_nutrition_to_diary(diary, make_mock_nutrition())

        diary.refresh_from_db()
        assert diary.status == DiaryEntry.StatusChoices.COMPLETED


@pytest.mark.django_db
class TestAnalyzeDiaryEntry:
    """
    end-to-end service 流程測試
    mock AI service，驗證整個流程的副作用(DB 寫入)
    """

    @pytest.fixture
    def mock_ai_service(self):
        service = MagicMock()
        service.model_name = 'gpt-4o-mini'
        service.analyze_food_nutrition.return_value = make_mock_nutrition()
        service.give_dietary_advice.return_value = make_mock_advice()
        return service

    def test_creates_ai_analysis_record(self, user, mock_ai_service):
        """完整分析後應建立 AIAnalysis 紀錄"""
        diary = DiaryEntryFactory(user=user, food_name='雞腿便當')

        with patch('diary.services.get_ai_service', return_value=mock_ai_service):
            DiaryService.analyze_diary_entry(diary)

        assert AIAnalysis.objects.filter(diary_entry=diary).exists()

    def test_ai_analysis_has_correct_data(self, user, mock_ai_service):
        diary = DiaryEntryFactory(user=user, food_name='雞腿便當')

        with patch('diary.services.get_ai_service', return_value=mock_ai_service):
            DiaryService.analyze_diary_entry(diary)

        analysis = AIAnalysis.objects.get(diary_entry=diary)
        assert analysis.nutrition_score == 75
        assert analysis.status == AIAnalysis.StatusChoices.COMPLETED
        assert '鈉' in analysis.exceeded_nutrients

    def test_diary_nutrition_filled_after_analysis(self, user, mock_ai_service):
        """分析後日記的營養素欄位應被填入"""
        diary = DiaryEntryFactory(user=user, food_name='雞腿便當')

        with patch('diary.services.get_ai_service', return_value=mock_ai_service):
            DiaryService.analyze_diary_entry(diary)

        diary.refresh_from_db()
        assert float(diary.calories) == 550.0
        assert diary.status == DiaryEntry.StatusChoices.COMPLETED

    def test_uses_food_cache_when_available(self, user, mock_ai_service):
        """有快取時，不應呼叫 AI 的 analyze_food_nutrition"""
        FoodNutritionCacheFactory(food_name='滷肉飯', calories=400)
        diary = DiaryEntryFactory(user=user, food_name='滷肉飯')

        with patch('diary.services.get_ai_service', return_value=mock_ai_service):
            DiaryService.analyze_diary_entry(diary)

        mock_ai_service.analyze_food_nutrition.assert_not_called()
        # give_dietary_advice 仍應被呼叫
        mock_ai_service.give_dietary_advice.assert_called_once()
        