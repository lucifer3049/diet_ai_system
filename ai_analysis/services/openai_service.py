import json
import logging
from openai import OpenAI
from decouple import config
from .base import BaseAIService, NutritionAnalysisResult, DietaryAdviceResult

logger = logging.getLogger(__name__)


class OpenAIService(BaseAIService):
    """
    繼承 BaseAIService，必須使用 analyze_diet 方法
    """

    def __init__(self):
        # 透過.env環境變數讀取AI的API KEY 以及使用模型，避免寫死模型
        self.client = OpenAI(api_key=config('OPENAI_API_KEY'))
        self.model_name = config('OPENAI_MODEL', default='gpt-4o-mini')
    
    def _call_api(self, prompt: str) -> str:
        """
        統一 API 呼叫方法，方便未來如果要換模型或調整參數，只需要修改這裡 
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位專業的營養師，請使用繁體中文回覆，並嚴格按照指定的 JSON 格式輸出。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def analyze_food_nutrition(self, food_name: str, portion_description: str = '') -> NutritionAnalysisResult:
        prompt = self._build_nutrition_prompt(food_name, portion_description)

        try:
            logger.info(f"OpenAI 分析食物營養: {food_name}")
            raw_text = self._call_api(prompt)
            parsed = json.loads(raw_text)

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
            logger.error(f"OpenAI 營養分析 JSON 解析失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI API 呼叫失敗: {e}")
            raise
    
    def give_dietary_advice(self, diary_entry_data: dict, user_profile: dict, daily_needs: dict) -> DietaryAdviceResult:
        prompt = self._build_advice_prompt(diary_entry_data, user_profile, daily_needs)

        try:
            logger.info("OpenAI 給予飲食建議")
            raw_text = self._call_api(prompt)
            parsed = json.loads(raw_text)

            return DietaryAdviceResult(
                summary=parsed.get('summary', ''),
                exceeded_nutrients=parsed.get('exceeded_nutrients', []),
                lacking_nutrients=parsed.get('lacking_nutrients', []),
                next_meal_suggestions=parsed.get('next_meal_suggestions', []),
                nutrition_score=int(parsed.get('nutrition_score', 70)),
                raw_response=raw_text
            )
        except json.JSONDecodeError as e:
            logger.error(f"OpenAI 飲食建議 JSON 解析失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI API 呼叫失敗: {e}")
            raise