from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """
    AI 分析結果的資料結構
    dataclass : 自動產生 __init__、__repr__等方法的 class
    統一 OpenAI 和 Gemini 的回傳格式
    """

    summary: str # 整體分析摘要
    suggestions: list # 建議飲食
    nutrition_score: int # 營養評分
    raw_response: str # AI 原始的回應 debug使用


class BaseAIService(ABC):
    """
    抽象基底 class
    ABC: Abstract Base Class，不能直接使用，只能被繼承

    為什麼用抽象 class
    1. 強迫所有class 都要實作 analyze_diet 方法
    2. 確保介面一致，View 呼叫時不需要知道底層用那個AI
    """

    @abstractmethod
    def analyze_diet(self, diary_data: dict, user_data: dict) -> AnalysisResult:
        """
        分析飲食紀錄

        Args:
            diary_data: 飲食資料(餐別、食物、營養總量)
            user_data: 使用者記錄(身高、體重、木鰾)

        Returns:
            AnalysisResult: 統一格式的分析結果
        """
        pass

    def _build_prompt(self, diary_data: dict, user_data: dict) -> str:
        """
        建立AI的prompt(提示詞)

        為了讓 OpenAi 和 Gemini 用一樣的提示詞，就不需要重複寫了
        """

        meal_type_map = {
            'breakfast': '早餐',
            'lunch': '午餐',
            'dinner': '晚餐',
            'snack': '點心',
        }

        foods_text = '\n'.join([
            f" - {item['food_name']} {item['amount_g']}g"
            for item in diary_data.get('foods', [])
        ])

        user_info = f"""
使用者資訊:
- 身高 : {user_data.get('height', '未提供')} CM
- 體重 : {user_data.get('weight', '未提供')} KG
- BMI : {user_data.get('bmi', '未提供')} 
- 飲食目標 : {user_data.get('goal', '維持體重')}
- 每日熱量目標 : {user_data.get('daily_calorie_target', '未提供')} kcal
"""
        
        prompt = f"""你是一位專業的營養師，請根據以下飲食紀錄給予專業分析和建議。
        
{user_info}

飲食紀錄: 
餐別: {meal_type_map.get(diary_data.get('meal_type', ''), '未知')}
日期: {diary_data.get('date', '未知')}

食物清單:
{foods_text}

營養攝取總量:
- 熱量: {diary_data.get('total_calories', 0)} kcal
- 蛋白質: {diary_data.get('total_protein', 0)} g
- 碳水化合物(醣類): {diary_data.get('total_carbs', 0)} g
- 脂肪: {diary_data.get('total_fat', 0)} g
- 膳食纖維: {diary_data.get('total_fiber', 0)} g

請用以下 JSON 格式回應 (只回應 JSON， 不要回應其他文字):
{{
    "summary": "整體飲食分析摘要,
    "suggestions": [
        "具體建議 1",
        "具體建議 2",
        "具體建議 3"
    ],
    "nutrition_score": 85
}}

評分標準:
- 90-100:營養非常均衡
- 70-89:大致良好，有小幅改善空間
- 50-69:有改善空間
- 50以下:兄弟你還好嗎?
        """
        return prompt
