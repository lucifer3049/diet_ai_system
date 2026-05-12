"""
測試 Celery Task 的行為邏輯：
- 正確觸發分析流程
- 跳過已分析的日記
- 失敗時正確標記狀態
- 優雅處理不存在的日記 ID

測試策略：
  Mock DiaryService.analyze_diary_entry → 只驗證 task 本身的控制流程
  不依賴真實 AI 呼叫或外部服務
"""
import pytest
from unittest.mock import patch, call
from diary.models import DiaryEntry
from diary.tasks import analyze_diary_entry_task
from celery.exceptions import Retry


@pytest.mark.django_db
class TestAnalyzeDiaryEntryTask:

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_processes_pending_diary(self, mock_analyze, pending_diary):
        """PENDING 狀態的日記應完整執行分析流程"""
        analyze_diary_entry_task.apply(args=[pending_diary.id])
        mock_analyze.assert_called_once_with(pending_diary)

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_sets_processing_status_before_analysis(self, mock_analyze, pending_diary):
        """分析執行前應先將狀態設為 PROCESSING，確保 UI 可以顯示進度"""
        captured_status = []

        def capture_during_analysis(diary):
            diary.refresh_from_db()
            captured_status.append(diary.status)

        mock_analyze.side_effect = capture_during_analysis
        analyze_diary_entry_task.apply(args=[pending_diary.id])

        assert captured_status[0] == DiaryEntry.StatusChoices.PROCESSING

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_skips_completed_diary(self, mock_analyze, completed_diary):
        """已完成分析的日記不應重複執行（冪等性保護）"""
        analyze_diary_entry_task.apply(args=[completed_diary.id])
        mock_analyze.assert_not_called()

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_skips_failed_diary(self, mock_analyze, failed_diary):
        """已標記失敗的日記不應自動重試（需透過 AI 分析端點手動觸發）"""
        analyze_diary_entry_task.apply(args=[failed_diary.id])
        mock_analyze.assert_not_called()

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_skips_processing_diary(self, mock_analyze, pending_diary):
        """PROCESSING 狀態表示有其他 worker 正在處理，應跳過（防止重複分析）"""
        pending_diary.status = DiaryEntry.StatusChoices.PROCESSING
        pending_diary.save(update_fields=['status'])

        analyze_diary_entry_task.apply(args=[pending_diary.id])
        mock_analyze.assert_not_called()

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_marks_diary_as_failed_on_exception(self, mock_analyze, pending_diary):
        """AI 分析拋出例外時，diary status 應標記為 FAILED"""
        mock_analyze.side_effect = Exception("OpenAI API timeout")

        with pytest.raises((Retry, Exception)):
            analyze_diary_entry_task.apply(args=[pending_diary.id])

        pending_diary.refresh_from_db()
        assert pending_diary.status == DiaryEntry.StatusChoices.FAILED

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_handles_nonexistent_diary_gracefully(self, mock_analyze):
        """找不到指定的 diary ID 時應靜默處理，不拋出未捕捉的例外"""
        # 不應 raise，也不應呼叫 analyze
        analyze_diary_entry_task.apply(args=[99999])
        mock_analyze.assert_not_called()

    @patch('diary.tasks.DiaryService.analyze_diary_entry')
    def test_failed_status_persisted_to_db(self, mock_analyze, pending_diary):
        """失敗狀態應正確寫入資料庫，不只是記憶體中的改變"""
        mock_analyze.side_effect = ValueError("Invalid nutrition data")

        with pytest.raises((Retry, Exception)):
            analyze_diary_entry_task.apply(args=[pending_diary.id])

        fresh = DiaryEntry.objects.get(id=pending_diary.id)
        assert fresh.status == DiaryEntry.StatusChoices.FAILED
