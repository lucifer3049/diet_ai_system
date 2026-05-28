import pytest
import json
import httpx
from unittest.mock import patch, MagicMock
from openai import APITimeoutError
from ai_analysis.services.openai_service import OpenAIService
from ai_analysis.services.gemini_service import GeminiService
from ai_analysis.services.base import NutritionAnalysisResult, clamp_nutrition


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


class TestNutritionClamp:
    """clamp_nutrition：把 AI 越界的營養值修正到合理範圍。"""

    def test_negative_clamped_to_zero(self):
        assert clamp_nutrition('calories', -50.0) == 0.0

    def test_over_upper_bound_clamped(self):
        # calories 上限 10000
        assert clamp_nutrition('calories', 999999.0) == 10000.0

    def test_normal_value_unchanged(self):
        assert clamp_nutrition('protein', 30.0) == 30.0

    def test_clamp_applied_in_analysis(self):
        """解析 AI 回應時，越界值應被 clamp，不會原樣進入結果。"""
        with patch('ai_analysis.services.openai_service.OpenAI'):
            svc = OpenAIService()
        mock_response = json.dumps({'calories': -10, 'protein': 999999})
        with patch.object(svc, '_call_api', return_value=mock_response):
            result = svc.analyze_food_nutrition('怪食物')
        assert result.calories == 0.0          # 負值 → 0
        assert result.protein == 1000.0        # 超過 protein 上限 1000


class TestOpenAIServiceRetry:
    """tenacity：暫時性錯誤重試、永久性錯誤不重試。"""

    @pytest.fixture
    def service(self):
        with patch('ai_analysis.services.openai_service.OpenAI'):
            svc = OpenAIService()
            svc.model_name = 'gpt-4o-mini'
            return svc

    @staticmethod
    def _timeout_error():
        return APITimeoutError(request=httpx.Request('POST', 'http://test'))

    @staticmethod
    def _ok_response(content='{}'):
        resp = MagicMock()
        resp.choices[0].message.content = content
        return resp

    def test_retries_transient_then_succeeds(self, service):
        """逾時兩次後第三次成功 → _call_api 回傳結果，共呼叫 3 次。"""
        service.client.chat.completions.create.side_effect = [
            self._timeout_error(),
            self._timeout_error(),
            self._ok_response('{"ok": true}'),
        ]
        with patch('time.sleep'):  # 跳過 tenacity 的退避等待，加速測試
            result = service._call_api('prompt')
        assert result == '{"ok": true}'
        assert service.client.chat.completions.create.call_count == 3

    def test_gives_up_after_max_attempts(self, service):
        """一直逾時 → 試滿 3 次後原樣拋出 APITimeoutError。"""
        service.client.chat.completions.create.side_effect = self._timeout_error()
        with patch('time.sleep'):
            with pytest.raises(APITimeoutError):
                service._call_api('prompt')
        assert service.client.chat.completions.create.call_count == 3

    def test_non_transient_not_retried(self, service):
        """非暫時性錯誤（如 ValueError）不重試，呼叫一次即拋出。"""
        service.client.chat.completions.create.side_effect = ValueError('boom')
        with patch('time.sleep'):
            with pytest.raises(ValueError):
                service._call_api('prompt')
        assert service.client.chat.completions.create.call_count == 1


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
            