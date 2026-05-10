import logging
from celery import shared_task
from .models import DiaryEntry
from .services import DiaryService

logger = logging.getLogger(__name__)

@shared_task(
    bind=True, # 讓task 可以存取自己(self)
    max_retries=3, #失敗最多重試3次
    default_retry_delay=30, # 重試間隔30秒
)
def analyze_diary_entry_task(self, diary_entry_id: int):
    """
    執行AI分析

    為什麼傳 id 而不是物件:
    Celery Task 的參數要能被序列化成 JSON
    Django Model 物件不能直接序列化，所以傳入id
    """
    logger.info(f"開始分析日記，diary_id={diary_entry_id}")

    try:
        diary_entry = DiaryEntry.objects.get(id=diary_entry_id)

        if diary_entry.status != DiaryEntry.StatusChoices.PENDING:
            logger.info(f"日記以分析過，跳過，diary_id={diary_entry_id}")
            return
        
        # 更新狀態為分析中
        diary_entry.status = DiaryEntry.StatusChoices.PROCESSING
        diary_entry.save(update_fields=['status'])

        DiaryService.analyze_diary_entry(diary_entry)
        logger.info(f"分析完成，diary_id={diary_entry_id}")
    except DiaryEntry.DoesNotExist:
        logger.error(f"找不到日記，diary_id={diary_entry_id}")
    except Exception as exc:
        logger.error(f"分析失敗，diary_id={diary_entry_id}，錯誤:{exc}")

        # 更新狀態為失敗
        DiaryEntry.objects.filter(id=diary_entry_id).update(status=DiaryEntry.StatusChoices.FAILED)

        raise self.retry(exc=exc)