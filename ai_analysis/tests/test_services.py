import pytest
import json
from unittest.mock import patch, MagicMock
from ai_analysis.services.openai_service import OpenAIService
from ai_analysis.services.gemini_service import GeminiService
from ai_analysis.services.base import NutritionAnalysisResult


class TestOpenAIServiceNutritionAnalysis:
    """
    測試 OpenAIService.analyze_food_nutrition
    關鍵：mock _call_api，測試解析邏輯是否正確
    """

    @pytest.fixture
    def service(self):
        with patch('ai_analysis.services.openai_service.OpenAI'):
            svc = OpenAIService()
            svc.model_name = 'gpt-4o-mini'
            return svc

    def test_parse_valid_response(self, service):
        mock_response = json.dumps({
            "calories": 550.0,
            "protein": 30.0,
            "fat": 20.0,
            "saturated_fat": 5.0,
            "trans_fat": 0.1,
            "carbohydrates": 60.0,
            "sugar": 10.0,
            "sodium": 800.0,
            "food_description": "雞腿便當，含米飯約200g"
        })

        with patch.object(service, '_call_api', return_value=mock_response):
            result = service.analyze_food_nutrition("雞腿便當")

        assert isinstance(result, NutritionAnalysisResult)
        assert result.calories == 550.0
        assert result.protein == 30.0
        assert result.food_description == "雞腿便當，含米飯約200g"

    def test_raises_on_invalid_json(self, service):
        with patch.object(service, '_call_api', return_value="not valid json"):
            with pytest.raises(json.JSONDecodeError):
                service.analyze_food_nutrition("雞腿便當")

    def test_handles_missing_fields_gracefully(self, service):
        """AI 回應缺少某些欄位時，應使用預設值 0"""
        mock_response = json.dumps({
            "calories": 300.0,
            "food_description": "簡單食物"
            # 故意缺少 protein, fat 等欄位
        })

        with patch.object(service, '_call_api', return_value=mock_response):
            result = service.analyze_food_nutrition("簡單食物")

        assert result.protein == 0.0
        assert result.fat == 0.0

    def test_prompt_contains_food_name(self, service):
        """確認 prompt 有帶入正確的食物名稱"""
        with patch.object(service, '_call_api', return_value='{}') as mock_api:
            try:
                service.analyze_food_nutrition("牛肉麵", "大碗")
            except Exception:
                pass
            
            call_args = mock_api.call_args[0][0]
            assert "牛肉麵" in call_args
            assert "大碗" in call_args


class TestAIServiceFactory:
    def test_get_openai_service(self):
        from ai_analysis.services import get_ai_service
        with patch('ai_analysis.services.openai_service.OpenAI'):
            service = get_ai_service('openai')
        assert isinstance(service, OpenAIService)

    def test_get_gemini_service(self):
        from ai_analysis.services import get_ai_service
        with patch('ai_analysis.services.gemini_service.genai'):
            service = get_ai_service('gemini')
        assert isinstance(service, GeminiService)

    def test_invalid_provider_raises_value_error(self):
        from ai_analysis.services import get_ai_service
        with pytest.raises(ValueError, match="不支援的 AI provider"):
            get_ai_service('invalid_provider')
            