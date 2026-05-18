import logging
from .models import DiaryEntry
from nutrition.models import FoodNutritionCache
from ai_analysis.models import AIAnalysis
from ai_analysis.services import get_ai_service
from ai_analysis.services.base import NutritionAnalysisResult
from nutrition.cache import get_cached_nutrition, set_cached_nutrition
from dataclasses import asdict

logger = logging.getLogger(__name__)

class DiaryService:
    """
    飲食日記邏輯
    View 只需要呼叫這裡，這裡裡負責處理業務邏輯
    """

    @staticmethod
    def get_nutrition_from_cache_or_ai(
        food_name: str,
        portion_description: str,
        service
    ) -> NutritionAnalysisResult:
        """
        三層資料來源：

        L1 Redis Cache
        L2 Database Cache
        L3 AI API
        """

        normalized_name = food_name.strip().lower()

        # L1 Redis Cache
        redis_cached = get_cached_nutrition(normalized_name)

        if redis_cached:
            logger.info(f"Redis cache hit: {normalized_name}")

            return NutritionAnalysisResult(**redis_cached)

        # L2 Database Cache
        db_cached = FoodNutritionCache.objects.filter(
            food_name__iexact=normalized_name
        ).first()

        if db_cached:
            logger.info(f"DB cache hit: {normalized_name}")

            db_cached.hit_count += 1
            db_cached.save(update_fields=['hit_count', 'updated_at'])

            result = NutritionAnalysisResult(
                calories=float(db_cached.calories),
                protein=float(db_cached.protein),
                fat=float(db_cached.fat),
                saturated_fat=float(db_cached.saturated_fat),
                trans_fat=float(db_cached.trans_fat),
                carbohydrates=float(db_cached.carbohydrates),
                sugar=float(db_cached.sugar),
                sodium=float(db_cached.sodium),
                food_description=db_cached.food_description,
                raw_response='{"source":"db_cache"}'
            )

            # 回填 Redis
            set_cached_nutrition(
                normalized_name,
                asdict(result)
            )

            return result

        logger.info(f"AI API call: {normalized_name}")

        nutrition_result = service.analyze_food_nutrition(
            food_name=food_name,
            portion_description=portion_description,
        )

        # 存 DB
        FoodNutritionCache.objects.create(
            food_name=normalized_name,
            calories=nutrition_result.calories,
            protein=nutrition_result.protein,
            fat=nutrition_result.fat,
            saturated_fat=nutrition_result.saturated_fat,
            trans_fat=nutrition_result.trans_fat,
            carbohydrates=nutrition_result.carbohydrates,
            sugar=nutrition_result.sugar,
            sodium=nutrition_result.sodium,
            food_description=nutrition_result.food_description,
            ai_model_used=service.model_name,
        )

        # 存 Redis
        set_cached_nutrition(
            normalized_name,
            asdict(nutrition_result)
        )

        return nutrition_result
    
    @staticmethod
    def save_nutrition_to_diary(
        diary_entry: DiaryEntry,
        nutrition_result: NutritionAnalysisResult
    ) -> None:
        """
        把AI回傳結果存到資料庫
        只負責存資料
        """
        diary_entry.calories = nutrition_result.calories
        diary_entry.protein = nutrition_result.protein
        diary_entry.fat = nutrition_result.fat
        diary_entry.saturated_fat = nutrition_result.saturated_fat
        diary_entry.trans_fat = nutrition_result.trans_fat
        diary_entry.carbohydrates = nutrition_result.carbohydrates
        diary_entry.sugar = nutrition_result.sugar
        diary_entry.sodium = nutrition_result.sodium
        diary_entry.status = DiaryEntry.StatusChoices.COMPLETED
        diary_entry.save()

    @staticmethod
    def build_diary_data(diary_entry: DiaryEntry) -> dict:
        """整理需要傳給AI的資料"""

        return {
            'food_name': diary_entry.food_name,
            'meal_type': diary_entry.get_meal_type_display(),
            'portion_description': diary_entry.portion_description,
            'calories': float(diary_entry.calories or 0),
            'protein': float(diary_entry.protein or 0),
            'fat': float(diary_entry.fat or 0),
            'saturated_fat': float(diary_entry.saturated_fat or 0),
            'trans_fat': float(diary_entry.trans_fat or 0),
            'carbohydrates': float(diary_entry.carbohydrates or 0),
            'sugar': float(diary_entry.sugar or 0),
            'sodium': float(diary_entry.sodium or 0),
        }
    
    @staticmethod
    def build_user_profile(user) -> dict:
        """整理要傳給AI的使用者資料"""

        return {
            'gender': user.get_gender_display() if user.gender else '未提供',
            'age': user.age,
            'height': float(user.height) if user.height else None,
            'weight': float(user.weight) if user.weight else None,
            'bmi': user.bmi,
            'goal': user.get_goal_display(),
        }

    @classmethod
    def analyze_diary_entry(cls, diary_entry: DiaryEntry) -> dict:
        """
        AI分析流程
        這是對外的主要入口，View 只需要呼叫這一個方法

        1. 取得營養資料 (本地資料或AI分析)
        2. 儲存營養日記到本地資料庫
        3. 取得飲食建議
        4. 存入 AI 分析結果
        """

        user = diary_entry.user
        provider = user.preferred_ai_provider
        service = get_ai_service(provider)
        food_name = diary_entry.food_name.strip()

        # 取得營養資料
        nutrition_result = cls.get_nutrition_from_cache_or_ai(
            food_name=food_name,
            portion_description=diary_entry.portion_description,
            service=service,
        )

        # 存回日記資料庫
        cls.save_nutrition_to_diary(diary_entry, nutrition_result)

        # 取得飲食建議
        diary_data = cls.build_diary_data(diary_entry)
        user_profile = cls.build_user_profile(user)
        daily_needs = user.daily_nutrition_needs or {}

        advice_result = service.give_dietary_advice(diary_data, user_profile, daily_needs)

        # 存入AI分析結果
        AIAnalysis.objects.create(
            user=user,
            diary_entry=diary_entry,
            prompt_sent=f"食物分析：{food_name}",
            raw_response=advice_result.raw_response,
            summary=advice_result.summary,
            suggestions=advice_result.next_meal_suggestions,
            exceeded_nutrients=advice_result.exceeded_nutrients,
            lacking_nutrients=advice_result.lacking_nutrients,
            nutrition_score=advice_result.nutrition_score,
            status=AIAnalysis.StatusChoices.COMPLETED,
            ai_model_used=f"{provider}:{service.model_name}",
        )
