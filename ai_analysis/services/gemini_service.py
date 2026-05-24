import json
import logging
from google import genai
from google.genai import types
from decouple import config
from .base import BaseAIService, NutritionAnalysisResult, DietaryAdviceResult

logger = logging.getLogger(__name__)


class GeminiService(BaseAIService):

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or config('GEMINI_API_KEY', default=None)
        if not key:
            raise ValueError("Gemini API key 未設定：請在個人設定填入 API key 或在伺服器 .env 設定 GEMINI_API_KEY")
        self.client = genai.Client(api_key=key)
        self.model_name = model or config('GEMINI_MODEL_NAME', default='gemini-2.5-flash')

    def _call_api(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.7,
            )
        )
        return response.text

    def _do_call_vision_api(self, image_data: bytes, mime_type: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=image_data, mime_type=mime_type),
                types.Part.from_text(text=self._build_vision_prompt()),
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.4,
            )
        )
        return response.text

    def analyze_food_nutrition(self, food_name: str, portion_description: str = '') -> NutritionAnalysisResult:
        prompt = self._build_nutrition_prompt(food_name, portion_description)
        try:
            logger.info(f"Gemini 分析食物營養: {food_name}")
            raw_text = self._call_api(prompt)
            parsed = json.loads(self._clean_json_response(raw_text))
            return NutritionAnalysisResult(
                calories=float(parsed.get('calories', 0)),
                protein=float(parsed.get('protein', 0)),
                fat=float(parsed.get('fat', 0)),
                saturated_fat=float(parsed.get('saturated_fat', 0)),
                trans_fat=float(parsed.get('trans_fat', 0)),
                carbohydrates=float(parsed.get('carbohydrates', 0)),
                sugar=float(parsed.get('sugar', 0)),
                sodium=float(parsed.get('sodium', 0)),
                food_description=parsed.get('food_description', ''),
                raw_response=raw_text
            )
        except json.JSONDecodeError as e:
            logger.error(f"Gemini 營養分析 JSON 解析失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            raise

    def give_dietary_advice(self, diary_entry_data: dict, user_profile: dict, daily_needs: dict) -> DietaryAdviceResult:
        prompt = self._build_advice_prompt(diary_entry_data, user_profile, daily_needs)
        try:
            logger.info("Gemini 給予飲食建議")
            raw_text = self._call_api(prompt)
            parsed = json.loads(self._clean_json_response(raw_text))
            return DietaryAdviceResult(
                summary=parsed.get('summary', ''),
                exceeded_nutrients=parsed.get('exceeded_nutrients', []),
                lacking_nutrients=parsed.get('lacking_nutrients', []),
                next_meal_suggestions=parsed.get('next_meal_suggestions', []),
                nutrition_score=int(parsed.get('nutrition_score', 70)),
                raw_response=raw_text
            )
        except json.JSONDecodeError as e:
            logger.error(f"Gemini 建議 JSON 解析失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            raise
