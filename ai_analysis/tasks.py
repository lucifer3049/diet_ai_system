import logging
from celery import shared_task
from diary.models import DiaryEntry

from .analysis_service import AIAnalysisService, DiaryNotReadyError

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def reanalyze_diary_task(self, diary_entry_id: int, provider: str):
    """
    重新指定日記進行飲食建議分析
    用於 POST /api/v1/ai/analyze/{diary_id}/ 的非同步
    """

    logger.info(f"開始飲食建議分析，diary_id={diary_entry_id}")

    try:
        diary_entry = DiaryEntry.objects.get(id=diary_entry_id)
        service = AIAnalysisService()
        service.analyze_diary(diary_entry, provider)
        logger.info(f"飲食建議分析完成，diary_id={diary_entry_id}")
    except DiaryEntry.DoesNotExist:
        logger.error(f"找不到日誌，diary_id={diary_entry_id}")
    except DiaryNotReadyError as e:
        logger.warning(f"日誌尚未準備好，diary_id={diary_entry_id}，原因: {e}")
    except Exception as exc:
        logger.error(f"飲食建議分析失敗，diary_id={diary_entry_id}，錯誤:{exc}")
        raise self.retry(exc=exc)