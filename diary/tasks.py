import logging
from celery import shared_task
from .models import DiaryEntry
from .services import DiaryService

logger = logging.getLogger(__name__)


# 注意：這兩個 task「不自動 retry」。
# 暫時性錯誤（OpenAI 503 / timeout / rate limit）已在 AI 呼叫層用 tenacity 就地重試；
# 走到這裡的失敗代表永久性錯誤或 tenacity 已用盡 → 標記 FAILED，由使用者手動觸發重分析。
# 因此不需要 bind=True / max_retries（之前那組設定沒有 self.retry 配合，其實從未生效）。


@shared_task
def analyze_diary_entry_task(diary_entry_id: int):
    """
    執行AI分析

    為什麼傳 id 而不是物件:
    Celery Task 的參數要能被序列化成 JSON
    Django Model 物件不能直接序列化，所以傳入id
    """
    logger.info(f"開始分析日記，diary_id={diary_entry_id}")

    # 原子搶占 PENDING→PROCESSING。False = 別的 worker 搶先（或 id 不存在）→ 安全跳過。
    if not DiaryService.begin_processing(diary_entry_id):
        logger.info(f"跳過分析(已被處理或不存在)，diary_id={diary_entry_id}")
        return

    try:
        diary_entry = DiaryEntry.objects.select_related('user').get(id=diary_entry_id)
        DiaryService.analyze_diary_entry(diary_entry)
        logger.info(f"分析完成，diary_id={diary_entry_id}")
    except Exception as exc:
        logger.error(f"分析失敗，diary_id={diary_entry_id}，錯誤:{exc}")
        DiaryEntry.objects.filter(id=diary_entry_id).update(
            status=DiaryEntry.StatusChoices.FAILED
        )
        raise


@shared_task
def analyze_diary_image_task(diary_entry_id: int):
    """
    圖片辨識 task，與文字分析 task 分開的原因:
    1. 不同的 retry 策略
    2. 未來可以獨立調整 concurrency
    3. 監控時可以分開統計成功率
    """
    logger.info(f"開始圖片辨識，diary_id={diary_entry_id}")

    if not DiaryService.begin_processing(diary_entry_id):
        logger.info(f"圖片辨識跳過(已被處理或不存在)，diary_id={diary_entry_id}")
        return

    try:
        diary_entry = DiaryEntry.objects.select_related('user').get(id=diary_entry_id)
        DiaryService.analyze_diary_image(diary_entry)
        logger.info(f"圖片辨識完成，diary_id={diary_entry_id}")
    except Exception as exc:
        logger.error(f"圖片辨識失敗，diary_id={diary_entry_id}，錯誤:{exc}")
        DiaryEntry.objects.filter(id=diary_entry_id).update(
            status=DiaryEntry.StatusChoices.FAILED
        )
        raise
