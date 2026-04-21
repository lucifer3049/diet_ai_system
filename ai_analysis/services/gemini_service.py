import json
import logging
import google.generativeai as genai
from decouple import config
from .base import BaseAIService, AnalysisResult

logger = logging.getLogger(__name__)

class GeminiService(BaseAIService):
    """
    Gemini AI 與 OpenAI 一樣的介面，但底層用gemini API
    """

    def __init__(self):
        genai.configure(api_key=config('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel(
            model_name=config('GEMINI_MODEL', default='gemini-1.5-flash'),
            generation_config={
                "response_mime_type": "application/json", # 回傳格式 JSON
                "temperature": 0.7,
            }
        )

    def analyze_diet(self, diary_data: dict, user_data: dict) -> AnalysisResult:
        prompt = self._build_prompt(diary_data, user_data)

        try:
            logger.info("呼叫 Gemini API")

            response = self.model.generate_content(prompt)
            raw_text = response.text
            parsed = json.loads(raw_text)

            return AnalysisResult(
                summary=parsed.get('summary', ''),
                suggestions=parsed.get('suggestions', []),
                nutrition_score=int(parsed.get('nutrition_score', 70)),
                raw_response=raw_text
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"Gemini 回應 JSON 解析失敗: {e}")

            return AnalysisResult(
                summary="分析完成，但結果格式異常",
                suggestions=["請重新嘗試分析"],
                nutrition_score=0,
                raw_response=str(e)
            )
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            raise

        