"""
L2.5 語意快取層：用 pgvector 做食物名稱的語意相似搜尋。

當 L2（精確比對）失敗時，嘗試找語意接近的快取項目。
例如：「豬排飯」沒有精確快取，但「排骨飯」有 → 相似度 > 0.92 → 直接使用。

嵌入向量由伺服器統一的 OPENAI_API_KEY 生成（使用成本低廉的 text-embedding-3-small）。
若伺服器未設定 OPENAI_API_KEY，則跳過 L2.5，直接進 L3 AI API。
"""
import logging
from typing import TYPE_CHECKING

from decouple import config

if TYPE_CHECKING:
    from nutrition.models import FoodNutritionCache

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92          # cosine similarity ≥ 0.92 才算相似
COSINE_DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD   # 即 0.08
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSIONS = 1536


class FoodVectorService:

    def __init__(self):
        api_key = config('OPENAI_API_KEY', default=None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 未設定，無法使用向量搜尋")
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    # ── 公開方法 ─────────────────────────────────────────────────────────────────

    def search_similar(self, food_name: str) -> 'FoodNutritionCache | None':
        """
        搜尋語意最相近的快取項目。
        回傳 similarity ≥ SIMILARITY_THRESHOLD 的第一筆，否則回傳 None。
        """
        from nutrition.models import FoodNutritionCache
        from pgvector.django import CosineDistance

        try:
            embedding = self._embed(food_name)
        except Exception as e:
            logger.warning(f"向量生成失敗，跳過 L2.5：{e}")
            return None

        try:
            result = (
                FoodNutritionCache.objects
                .exclude(embedding=None)
                .annotate(distance=CosineDistance('embedding', embedding))
                .filter(distance__lt=COSINE_DISTANCE_THRESHOLD)
                .order_by('distance')
                .first()
            )
            if result:
                similarity = round(1 - result.distance, 4)
                logger.info(
                    f"L2.5 vector hit: '{food_name}' → '{result.food_name}' "
                    f"(similarity={similarity})"
                )
            return result
        except Exception as e:
            logger.warning(f"向量搜尋失敗，跳過 L2.5：{e}")
            return None

    def store_embedding(self, cache_obj: 'FoodNutritionCache') -> None:
        """為一筆 FoodNutritionCache 生成並儲存 embedding。失敗時靜默略過。"""
        try:
            embedding = self._embed(cache_obj.food_name)
            cache_obj.embedding = embedding
            cache_obj.save(update_fields=['embedding'])
            logger.debug(f"Embedding 已儲存：{cache_obj.food_name}")
        except Exception as e:
            logger.warning(f"Embedding 儲存失敗（{cache_obj.food_name}）：{e}")

    # ── 內部方法 ─────────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.strip().lower(),
        )
        return response.data[0].embedding


def try_vector_search(food_name: str) -> 'FoodNutritionCache | None':
    """
    安全包裝：若 pgvector 未安裝或 key 未設定，靜默回傳 None。
    用於 DiaryService 的 L2.5 呼叫點。
    """
    try:
        svc = FoodVectorService()
        return svc.search_similar(food_name)
    except RuntimeError:
        # OPENAI_API_KEY 未設定
        return None
    except Exception as e:
        logger.warning(f"L2.5 向量搜尋例外，跳過：{e}")
        return None
