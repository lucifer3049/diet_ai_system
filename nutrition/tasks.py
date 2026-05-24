import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def sync_taiwan_fda_task(self):
    """
    Celery Beat 定時同步台灣 FDA 食品成分資料。
    由 settings.TAIWAN_FDA_SYNC_ENABLED 控制是否真正執行。
    settings.TAIWAN_FDA_CSV_URL 指定 CSV 下載位址。
    """
    if not getattr(settings, 'TAIWAN_FDA_SYNC_ENABLED', False):
        logger.info("Taiwan FDA 自動同步已停用（TAIWAN_FDA_SYNC_ENABLED=False），略過")
        return

    csv_url = getattr(settings, 'TAIWAN_FDA_CSV_URL', '')
    if not csv_url:
        logger.warning("TAIWAN_FDA_CSV_URL 未設定，無法自動下載，略過")
        return

    try:
        from nutrition.fda_importer import TaiwanFDAImporter
        importer = TaiwanFDAImporter()
        result = importer.import_from_url(csv_url)
        logger.info(
            f"FDA 同步完成：新增 {result['created']} 筆，"
            f"更新 {result['updated']} 筆，略過 {result['skipped']} 筆"
        )
    except Exception as exc:
        logger.error(f"FDA 同步失敗：{exc}")
        raise self.retry(exc=exc)
