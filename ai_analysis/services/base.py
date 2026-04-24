from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NutritionAnalysisResult:
    """AI 分析食物營養結果"""
    calories: float
    protein: float
    fat: float
    saturated_fat: float
    trans_fat: float
    carbohydrates: float
    sugar: float
    sodium: float
    food_description: str # AI 生成的食物描述
    raw_response: str


@dataclass
class DietaryAdviceResult:
    """AI 營養師建議的結果"""
    summary: str    # 這餐整題評價
    exceeded_nutrients: list # 攝取過多的營養素
    lacking_nutrients: list # 攝取不足的營養素
    next_meal_suggestions: list # 下一餐建議餐食
    nutrition_score: int # 營養評分
    raw_response: str


class BaseAIService(ABC):

    @abstractmethod
    def analyze_food_nutrition(
        self,
        food_name: str,
        portion_description: str = ''
    ) -> NutritionAnalysisResult:
        """
        分析食物營養素
        輸入:食物名稱 + 份量描述
        輸出:完整營養素數據
        """
        pass

    @abstractmethod
    def give_dietary_advice(
        self,
        diary_entry_data: dict,
        user_profile: dict,
        daily_needs: dict
    ) -> DietaryAdviceResult:
        """
        根據這餐的營養素 + 使用者資料 給出建議
        """
        pass

    def _build_nutrition_prompt(self, food_name: str, portion_description: str) -> str:
        portion_text = f"，份量：{portion_description}" if portion_description else ""
        return f"""你是一位專業的營養師和食品分析師。
請分析以下食物的營養成分，給出最接近真實的估算值。

食物:{food_name}{portion_text}

請嚴格用以下 JSON 格式回覆（只回覆 JSON):
{{
    "calories": 熱量數字(kcal),
    "protein": 蛋白質公克數(g),
    "fat": 總脂肪公克數(g),
    "saturated_fat": 飽和脂肪公克數(g),
    "trans_fat": 反式脂肪公克數(g),
    "carbohydrates": 碳水化合物公克數(g),
    "sugar": 糖公克數(g),
    "sodium": 鈉毫克數(mg),
    "food_description": "對這個食物的簡短描述，包含份量估算"
}}"""

    def _build_advice_prompt(
        self,
        diary_entry_data: dict,
        user_profile: dict,
        daily_needs: dict
    ) -> str:
        return f"""你是一位專業的營養師，請根據以下資訊給予飲食建議。

使用者資料:
- 性別:{user_profile.get('gender', '未提供')}
- 年齡:{user_profile.get('age', '未提供')} 歲
- 身高:{user_profile.get('height', '未提供')} 公分
- 體重:{user_profile.get('weight', '未提供')} 公斤
- BMI:{user_profile.get('bmi', '未提供')}
- 飲食目標:{user_profile.get('goal', '維持體重')}

每日建議攝取量:
- 熱量:{daily_needs.get('calories', '未知')} 大卡
- 蛋白質:{daily_needs.get('protein', '未知')} 克
- 脂肪:{daily_needs.get('fat', '未知')} 克
- 碳水化合物:{daily_needs.get('carbohydrates', '未知')} 克
- 鈉:{daily_needs.get('sodium', '未知')} 毫克

這餐內容:
- 食物:{diary_entry_data.get('food_name')}
- 時段:{diary_entry_data.get('meal_type')}
- 熱量:{diary_entry_data.get('calories')} 大卡
- 蛋白質:{diary_entry_data.get('protein')} 克
- 脂肪:{diary_entry_data.get('fat')} 克
- 飽和脂肪:{diary_entry_data.get('saturated_fat')} 克
- 反式脂肪:{diary_entry_data.get('trans_fat')} 克
- 碳水化合物:{diary_entry_data.get('carbohydrates')} 克
- 糖:{diary_entry_data.get('sugar')} 克
- 鈉:{diary_entry_data.get('sodium')} 毫克

請用以下 JSON 格式回覆（只回覆 JSON):
{{
    "summary": "這餐的整體評價(2-3句話)",
    "exceeded_nutrients": ["攝取過多的營養素1", "攝取過多的營養素2"],
    "lacking_nutrients": ["缺少的營養素1", "缺少的營養素2"],
    "next_meal_suggestions": [
        "具體的下一餐建議1",
        "具體的下一餐建議2",
        "具體的下一餐建議3"
    ],
    "nutrition_score": 評分數字
}}"""
    
