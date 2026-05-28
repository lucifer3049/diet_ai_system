import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# 單筆食物（每份）的營養值合理上限。AI 偶爾會回出 999999 或負數，
# 這些越界值若直接入庫會污染統計與後續建議，所以在解析時就 clamp 掉。
NUTRITION_BOUNDS = {
    'calories': 10000,
    'protein': 1000,
    'fat': 1000,
    'saturated_fat': 1000,
    'trans_fat': 1000,
    'carbohydrates': 2000,
    'sugar': 2000,
    'sodium': 100000,  # mg
}


def clamp_nutrition(field: str, value: float) -> float:
    """把營養值限制在 [0, 上限]。越界時記 warning 並回傳修正值。"""
    upper = NUTRITION_BOUNDS.get(field, float('inf'))
    clamped = min(max(value, 0.0), upper)
    if clamped != value:
        logger.warning(f"AI 營養值越界，已修正：{field}={value} → {clamped}")
    return clamped

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

@dataclass
class FoodComponent:
    """
    圖片辨識出的食物成份
    """
    name: str
    portion_description: str
    calories: float
    protein: float
    fat: float
    saturated_fat: float
    trans_fat: float
    carbohydrates: float
    sugar: float
    sodium: float

@dataclass
class ImageAnalysisResult:
    """圖片分析的結果"""
    components: List[FoodComponent]
    overall_description: str # 圖片辨識後對內容的描述
    raw_response: str


class BaseAIService(ABC):

    @abstractmethod
    def _call_api(self, prompt:str) -> str:
        pass

    @abstractmethod
    def _do_call_vision_api(self, image_data: bytes, mime_type: set) -> str:
        pass

    @abstractmethod
    def analyze_food_nutrition(self, food_name: str, portion_description: str = '') -> NutritionAnalysisResult:
        """
        分析食物營養素
        輸入:食物名稱 + 份量描述
        輸出:完整營養素數據
        """
        pass

    @abstractmethod
    def give_dietary_advice(self, diary_entry_data: dict, user_profile: dict, daily_needs: dict) -> DietaryAdviceResult:
        """
        根據這餐的營養素 + 使用者資料 給出建議
        """
        pass

    def analyze_food_image(self, image_data: bytes, mime_type: str) -> ImageAnalysisResult:
        """
        圖片辨識主流成，所有 provider 共用
        子類別只需要做 _do_call_vision_api
        """
        raw_text = self._call_vision_api(image_data, mime_type)
        return self._parse_image_result(raw_text)

    def _call_vision_api(self, image_data: bytes, mime_type: str) -> str:
        logger.info(f"[{self.__class__.__name__}] 圖片辨識開始")
        try:
            raw_text = self._do_call_vision_api(image_data, mime_type)
            logger.info(f"[{self.__class__.__name__}] 圖片辨識完成")
            return raw_text
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] 圖片辨識失敗: {e}")
            raise

    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """去除 AI 可能包裹的 markdown code fence（```json ... ```）"""
        text = raw_text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[-1]
            text = text.rsplit('```', 1)[0]
        return text.strip()

    def _parse_image_result(self, raw_text: str) -> ImageAnalysisResult:
        """圖片辨識結果解析，所有子類別共用"""
        parsed = json.loads(self._clean_json_response(raw_text))
        components = [
            FoodComponent(
                name=c.get('name', '未知食物'),
                portion_description=c.get('portion_description', ''),
                calories=clamp_nutrition('calories', float(c.get('calories', 0))),
                protein=clamp_nutrition('protein', float(c.get('protein', 0))),
                fat=clamp_nutrition('fat', float(c.get('fat', 0))),
                saturated_fat=clamp_nutrition('saturated_fat', float(c.get('saturated_fat', 0))),
                trans_fat=clamp_nutrition('trans_fat', float(c.get('trans_fat', 0))),
                carbohydrates=clamp_nutrition('carbohydrates', float(c.get('carbohydrates', 0))),
                sugar=clamp_nutrition('sugar', float(c.get('sugar', 0))),
                sodium=clamp_nutrition('sodium', float(c.get('sodium', 0))),
            )
            for c in parsed.get('components', [])
        ]
        return ImageAnalysisResult(
            components=components,
            overall_description=parsed.get('overall_description', ''),
            raw_response=raw_text
        )

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
    
    def _build_vision_prompt(self) -> str:
        return """你是一位專業的營養師和食物辨識專家。
請仔細分析這張食物照片，辨別出所有可見的食物成份。

請嚴格用以下 JSON 格式回覆 (只回覆 JSON):
{
    "overall_description": "對整體食物的描述，例如：雞肉飯便當，含白飯、雞肉絲、醃蘿蔔",
    "components": [
        {
            "name": "食物名稱，例如：白飯",
            "portion_description": "估算份量，例如:約150g",
            "calories": 熱量數字,
            "protein": 蛋白質克數,
            "fat": 脂肪克數,
            "saturated_fat": 飽和脂肪克數,
            "trans_fat": 反式脂肪克數,
            "carbohydrates": 碳水化合物克數,
            "sugar": 糖克數,
            "sodium": 鈉毫克數
        }
    ]
}

注意:
- 每個可見的食物成份都需要單獨列出
- 份量請根據照片中的視覺比例估算
- 如果看不清楚某個成份，給出合理估算值
"""
