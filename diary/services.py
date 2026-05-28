import logging
import mimetypes
from .models import DiaryEntry, DiaryComponent
from .dto import DiaryNutritionDTO
from nutrition.models import FoodNutritionCache
from ai_analysis.models import AIAnalysis
from ai_analysis.services import get_ai_service
from ai_analysis.services.base import NutritionAnalysisResult, ImageAnalysisResult
from nutrition.cache import get_cached_nutrition, set_cached_nutrition
from .state_machine import assert_legal_transition
from dataclasses import asdict
from decimal import Decimal
from django.db import transaction
from django.db.models import F


logger = logging.getLogger(__name__)

_NUTRITION_UPDATE_FIELDS = [
    'calories', 'protein', 'fat', 'saturated_fat',
    'trans_fat', 'carbohydrates', 'sugar', 'sodium', 'status',
]

class DiaryService:
    """
    飲食日記邏輯
    View 只需要呼叫這裡，這裡負責處理業務邏輯
    """

    @staticmethod
    def begin_processing(diary_entry_id: int) -> bool:
        """
        原子搶占：只有成功把 PENDING → PROCESSING 的 worker 回傳 True。

        為什麼用 filter().update() 而不是 get() 後判斷再 save()？
        後者是 check-then-act，兩個 worker 可能同時讀到 PENDING、各自往下跑，
        AI 被打兩次、錢花兩次。filter().update() 是 DB 端單一原子操作
        （UPDATE ... WHERE status='pending'），只有一個 worker 能把那一列改掉，
        回傳的 rowcount 就是「我有沒有搶到」。id 不存在時也回傳 0。
        """
        return DiaryEntry.objects.filter(
            id=diary_entry_id,
            status=DiaryEntry.StatusChoices.PENDING,
        ).update(status=DiaryEntry.StatusChoices.PROCESSING) > 0

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

            FoodNutritionCache.objects.filter(id=db_cached.id).update(
                hit_count=F('hit_count') + 1
            )

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
            set_cached_nutrition(normalized_name, asdict(result))

            return result

        # L2.5 pgvector 語意搜尋（找不到精確快取時，試試語意相似的）
        from nutrition.vector_service import try_vector_search
        similar = try_vector_search(normalized_name)
        if similar:
            result = NutritionAnalysisResult(
                calories=float(similar.calories),
                protein=float(similar.protein),
                fat=float(similar.fat),
                saturated_fat=float(similar.saturated_fat),
                trans_fat=float(similar.trans_fat),
                carbohydrates=float(similar.carbohydrates),
                sugar=float(similar.sugar),
                sodium=float(similar.sodium),
                food_description=similar.food_description,
                raw_response='{"source":"vector_cache"}',
            )
            set_cached_nutrition(normalized_name, asdict(result))
            return result

        logger.info(f"AI API call: {normalized_name}")

        nutrition_result = service.analyze_food_nutrition(
            food_name=food_name,
            portion_description=portion_description,
        )

        # get_or_create 防止併發重複寫入同一食物
        cache_obj, created = FoodNutritionCache.objects.get_or_create(
            food_name=normalized_name,
            defaults=dict(
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
        )

        # 非同步補存 embedding（不阻塞主流程）
        if created:
            from nutrition.vector_service import FoodVectorService
            try:
                FoodVectorService().store_embedding(cache_obj)
            except Exception:
                pass  # embedding 失敗不影響主流程

        # 存 Redis
        set_cached_nutrition(normalized_name, asdict(nutrition_result))

        return nutrition_result

    @staticmethod
    def _apply_nutrition(
        diary_entry: DiaryEntry,
        nutrition_result: NutritionAnalysisResult
    ) -> None:
        """
        把 AI 回傳的營養值套到記憶體中的 entry，並把狀態推進到 COMPLETED。
        不寫 DB —— 讓呼叫端決定何時、在哪個 transaction 內存檔。
        """
        assert_legal_transition(diary_entry.status, DiaryEntry.StatusChoices.COMPLETED)
        diary_entry.calories = nutrition_result.calories
        diary_entry.protein = nutrition_result.protein
        diary_entry.fat = nutrition_result.fat
        diary_entry.saturated_fat = nutrition_result.saturated_fat
        diary_entry.trans_fat = nutrition_result.trans_fat
        diary_entry.carbohydrates = nutrition_result.carbohydrates
        diary_entry.sugar = nutrition_result.sugar
        diary_entry.sodium = nutrition_result.sodium
        diary_entry.status = DiaryEntry.StatusChoices.COMPLETED

    @staticmethod
    def save_nutrition_to_diary(
        diary_entry: DiaryEntry,
        nutrition_result: NutritionAnalysisResult
    ) -> None:
        """把AI回傳結果存到資料庫，只更新營養欄位"""
        DiaryService._apply_nutrition(diary_entry, nutrition_result)
        diary_entry.save(update_fields=_NUTRITION_UPDATE_FIELDS)

    @staticmethod
    def build_diary_data(diary_entry: DiaryEntry) -> dict:
        """整理需要傳給AI的資料"""
        return DiaryNutritionDTO.from_entry(diary_entry).to_dict()

    @staticmethod
    def build_user_profile(user) -> dict:
        """整理要傳給AI的使用者資料"""
        return user.to_ai_profile()

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
        service = get_ai_service(
            provider=provider,
            api_key=user.get_api_key(provider),
            model=user.get_preferred_model(provider),
        )
        food_name = diary_entry.food_name.strip()

        # 取得營養資料
        nutrition_result = cls.get_nutrition_from_cache_or_ai(
            food_name=food_name,
            portion_description=diary_entry.portion_description,
            service=service,
        )

        # 把營養值套到記憶體中的 entry（給 build_diary_data 用），先不寫 DB
        cls._apply_nutrition(diary_entry, nutrition_result)

        # 組要給 AI 的資料
        diary_data = cls.build_diary_data(diary_entry)
        user_profile = cls.build_user_profile(user)
        daily_needs = user.daily_nutrition_needs or {}

        # 外部 AI 呼叫：務必在 transaction 之外。
        # 否則一筆 DB 交易會被這個 2~3 秒的 API 卡住，佔住連線、延長鎖的持有時間。
        advice_result = service.give_dietary_advice(diary_data, user_profile, daily_needs)

        # 兩個 DB 寫入綁進同一個 transaction：要嘛 entry 存檔 + AIAnalysis 都成功，
        # 要嘛一起 rollback。避免「entry 已 COMPLETED 但 AIAnalysis 沒建」的部分失敗。
        with transaction.atomic():
            diary_entry.save(update_fields=_NUTRITION_UPDATE_FIELDS)
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
                status=DiaryEntry.StatusChoices.COMPLETED,
                ai_model_used=f"{provider}:{service.model_name}",
            )

    @classmethod
    def analyze_diary_image(cls, diary_entry: DiaryEntry) -> None:
        """
        圖片辨識功能:
        1. 讀取圖片 bytes
        2. 呼叫 AI Vision API
        3. 建立 DiaryComponent 紀錄
        4. 彙總營養素 -> 更新 DiaryEntry
        5. 更新狀態為 COMPLETED

        用 transaction.atomic 確保資料一致性:
        components 全部建立成功 + DiaryEntry 更新，才算完成，只要其中一步失敗，全部 rollback
        """
        user = diary_entry.user
        provider = user.preferred_ai_provider
        service = get_ai_service(
            provider=provider,
            api_key=user.get_api_key(provider),
            model=user.get_preferred_model(provider),
        )

        # 讀取圖片
        image_data, mime_type = cls._read_image(diary_entry)

        # 呼叫 AI
        image_result = service.analyze_food_image(image_data, mime_type)

        # atomic 寫入，確保 components + DiaryEntry 同步完成
        with transaction.atomic():
            cls._save_components(diary_entry, image_result, provider)
            cls._aggregate_to_diary(diary_entry, image_result)

    @staticmethod
    def _read_image(diary_entry: DiaryEntry) -> tuple[bytes, str]:
        """從 ImageField 讀取原始 bytes 和 mime type"""
        image_field = diary_entry.image
        mime_type, _ = mimetypes.guess_type(image_field.name)
        mime_type = mime_type or 'image/jpeg'

        with image_field.open('rb') as f:
            return f.read(), mime_type

    @staticmethod
    def _save_components(
        diary_entry: DiaryEntry,
        image_result: ImageAnalysisResult,
        provider: str,
    ) -> None:
        """
        批次建立 DiaryComponent
        用 bulk_create 而不是逐筆建立
        10 個食物成份 = 1 次 INSERT，不是 10 次
        """
        components = [
            DiaryComponent(
                diary_entry=diary_entry,
                food_name=comp.name,
                portion_description=comp.portion_description,
                calories=Decimal(str(comp.calories)),
                protein=Decimal(str(comp.protein)),
                fat=Decimal(str(comp.fat)),
                saturated_fat=Decimal(str(comp.saturated_fat)),
                trans_fat=Decimal(str(comp.trans_fat)),
                carbohydrates=Decimal(str(comp.carbohydrates)),
                sugar=Decimal(str(comp.sugar)),
                sodium=Decimal(str(comp.sodium)),
                source=DiaryComponent.SourceChoices.AI_VISION,
            )
            for comp in image_result.components
        ]
        DiaryComponent.objects.bulk_create(components)

    @staticmethod
    def _aggregate_to_diary(
        diary_entry: DiaryEntry,
        image_result: ImageAnalysisResult,
    ) -> None:
        """將所有 components 的營養成份加總，填入 DiaryEntry"""
        assert_legal_transition(diary_entry.status, DiaryEntry.StatusChoices.COMPLETED)
        def _sum(field: str) -> Decimal:
            return Decimal(str(sum(getattr(c, field, 0) for c in image_result.components)))

        diary_entry.calories = _sum('calories')
        diary_entry.protein = _sum('protein')
        diary_entry.fat = _sum('fat')
        diary_entry.saturated_fat = _sum('saturated_fat')
        diary_entry.trans_fat = _sum('trans_fat')
        diary_entry.carbohydrates = _sum('carbohydrates')
        diary_entry.sugar = _sum('sugar')
        diary_entry.sodium = _sum('sodium')
        diary_entry.status = DiaryEntry.StatusChoices.COMPLETED
        diary_entry.save(update_fields=_NUTRITION_UPDATE_FIELDS)


