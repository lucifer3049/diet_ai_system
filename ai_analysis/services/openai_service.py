import json
import logging
from openai import OpenAI
from decouple import config
from .base import BaseAIService, AnalysisResult

logger = logging.getLogger(__name__)


class OpenAIService(BaseAIService):
    """
    繼承 BaseAIService，必須使用 analyze_diet 方法
    """

    def __init__(self):
        # 透過.env環境變數讀取AI的API KEY 以及使用模型，避免寫死模型
        self.client = OpenAI(api_key=config('OPENAI_API_KEY'))
        self.model = config('OPENAI_MODEL', default='gpt-4o-mini')

    def analyze_diet(self, diary_data: dict, user_data: dict) -> AnalysisResult:
        """
        呼叫 OpenAI API 分析飲食紀錄
        """

        prompt = self._build_prompt(diary_data, user_data) # base.py 設定的提示詞

        try:
            logger.info(f"呼叫 OpenAI API，模型:{self.model}")

            response = self.client.chat.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的營養師，請用繁體中文回復，並嚴格按照指定的JSON格式輸出。"
                    },
                    {
                        "role": "user",
                        "content":prompt
                    }
                ],
                temperature=0.7, # 0 = 嚴謹固定， 1 = 有創意但不穩定， 0.7 有創意且穩定
                max_tokens=1000, # 一次回復的字數上限
                response_format={"type": "json_object"}, # 回復格式 JSON 輸出
            )

            raw_text = response.choices[0].message.content
            parsed = json.loads(raw_text)

            return AnalysisResult(
                summary=parsed.get('summary', ''),
                suggestions=parsed.get('suggestions', []),
                nutrition_score=int(parsed.get('nutrition_score', 70)),
                raw_response=raw_text
            )
        except json.JSONDecodeError as e:
            # JSON 解析失敗時，讓系統不會崩潰
            logger.error(f"OpenAI API 回傳 JSON 解析分析: {e}")

            return AnalysisResult(
                summary="分析完成，但結果格式異常",
                suggestions=["請重新嘗試分析"],
                nutrition_score=0,
                raw_response=str(e)
            )
        except Exception as e:
            logger.error(f"OpenAI API 呼叫失敗:{e}")
            raise 
        

