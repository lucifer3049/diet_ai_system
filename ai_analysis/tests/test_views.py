"""
測試 AI 分析相關的兩個端點：
  POST /api/v1/ai/analyze/{diary_id}/   → AnalyzeDiaryView
  GET  /api/v1/ai/my-analyses/          → MyAnalysisListView

核心測試場景：
  - 已有分析結果 → 直接回傳 200(cache hit)
  - 正常觸發 → 202(非同步排程）
  - 日記尚未分析完(PENDING)→ 400
  - 日記分析失敗(FAILED)→ 400
  - 找不到日記或存取他人日記 → 404
  - 未認證 → 401
  - Request body 指定 provider 的優先順序

測試策略：
  mock reanalyze_diary_task.delay → 驗證 view 行為，不真正執行 Celery task
  不依賴外部 AI 服務
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from diary.models import DiaryEntry
from ai_analysis.models import AIAnalysis
from ai_analysis.tasks import reanalyze_diary_task

User = get_user_model()


def analyze_url(diary_id: int) -> str:
    return f'/api/v1/ai/analyze/{diary_id}/'


MY_ANALYSES_URL = '/api/v1/ai/my-analyses/'


@pytest.mark.django_db
class TestAnalyzeDiaryView:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client, user):
        self.client = authenticated_client
        self.user = user

    def test_returns_200_when_analysis_already_exists(self, completed_diary, ai_analysis):
        """已有 AIAnalysis 紀錄時直接回傳 200，不重新排程任務"""
        response = self.client.post(analyze_url(completed_diary.id))

        assert response.status_code == 200
        assert response.data['nutrition_score'] == 75
        assert response.data['summary'] == '這餐整體營養均衡，蛋白質攝取充足。'

    def test_cached_response_includes_all_analysis_fields(self, completed_diary, ai_analysis):
        response = self.client.post(analyze_url(completed_diary.id))
        assert response.status_code == 200
        for field in ['id', 'diary_entry', 'summary', 'nutrition_score',
                      'exceeded_nutrients', 'lacking_nutrients', 'status']:
            assert field in response.data, f"Missing field: {field}"

    def test_returns_202_when_analysis_triggered(self, completed_diary):
        """尚無分析結果且日記狀態正確時，應排程 Celery task 並回傳 202"""
        with patch.object(reanalyze_diary_task, 'delay') as mock_delay:
            response = self.client.post(analyze_url(completed_diary.id))

        assert response.status_code == 202
        assert 'message' in response.data

    def test_task_called_with_diary_id_and_provider(self, completed_diary):
        """task 應被呼叫，並帶入正確的 diary_id 與 provider"""
        with patch.object(reanalyze_diary_task, 'delay') as mock_delay:
            self.client.post(analyze_url(completed_diary.id))

        mock_delay.assert_called_once_with(
            completed_diary.id,
            self.user.preferred_ai_provider,  # 預設使用者偏好
        )

    def test_provider_in_request_body_takes_priority(self, completed_diary):
        """Request body 指定的 provider 應優先於使用者偏好設定"""
        with patch.object(reanalyze_diary_task, 'delay') as mock_delay:
            self.client.post(
                analyze_url(completed_diary.id),
                data={'provider': 'gemini'},
                format='json',
            )

        mock_delay.assert_called_once_with(completed_diary.id, 'gemini')

    def test_empty_provider_falls_back_to_user_preference(self, completed_diary):
        """Request body provider 為空時，應 fallback 至使用者偏好"""
        self.user.preferred_ai_provider = 'openai'
        self.user.save()

        with patch.object(reanalyze_diary_task, 'delay') as mock_delay:
            self.client.post(
                analyze_url(completed_diary.id),
                data={'provider': ''},
                format='json',
            )

        # provider='' 為 falsy，應使用使用者偏好
        mock_delay.assert_called_once_with(completed_diary.id, 'openai')

    def test_returns_400_when_diary_is_pending(self, pending_diary):
        """PENDING 狀態表示營養素分析尚未完成，不能進行飲食建議分析"""
        response = self.client.post(analyze_url(pending_diary.id))
        assert response.status_code == 400

    def test_returns_400_when_diary_is_failed(self, failed_diary):
        """FAILED 狀態的日記缺乏營養素資料，無法給予建議"""
        response = self.client.post(analyze_url(failed_diary.id))
        assert response.status_code == 400

    def test_400_response_contains_error_message(self, pending_diary):
        """400 回應應包含可讀的錯誤訊息"""
        response = self.client.post(analyze_url(pending_diary.id))
        assert response.status_code == 400
        assert 'error' in response.data

    def test_returns_404_for_nonexistent_diary(self):
        response = self.client.post(analyze_url(99999))
        assert response.status_code == 404

    def test_returns_404_for_other_users_diary(self, db):
        """不能存取其他使用者的日記（權限隔離）"""
        other_user = User.objects.create_user(
            username='other_user', password='Test1234!'
        )
        other_diary = DiaryEntry.objects.create(
            user=other_user,
            date=date.today(),
            meal_type='dinner',
            food_name='牛肉麵',
            status=DiaryEntry.StatusChoices.COMPLETED,
            calories=600, protein=25, fat=18,
            saturated_fat=4, trans_fat=0,
            carbohydrates=70, sugar=5, sodium=1200,
        )
        response = self.client.post(analyze_url(other_diary.id))
        assert response.status_code == 404

    def test_returns_401_when_unauthenticated(self, completed_diary):
        response = APIClient().post(analyze_url(completed_diary.id))
        assert response.status_code == 401

@pytest.mark.django_db
class TestMyAnalysisListView:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client, user):
        self.client = authenticated_client
        self.user = user

    def test_returns_my_analyses(self, ai_analysis):
        response = self.client.get(MY_ANALYSES_URL)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['nutrition_score'] == 75

    def test_returns_empty_list_when_no_analyses(self):
        response = self.client.get(MY_ANALYSES_URL)
        assert response.status_code == 200
        assert response.data == []

    def test_returns_analyses_ordered_by_newest_first(self, user, db):
        """多筆分析結果應依建立時間由新到舊排序"""
        from diary.models import DiaryEntry
        from ai_analysis.models import AIAnalysis

        def _make_diary(food_name):
            return DiaryEntry.objects.create(
                user=user, date=date.today(), meal_type='lunch',
                food_name=food_name, status=DiaryEntry.StatusChoices.COMPLETED,
                calories=500, protein=20, fat=15, saturated_fat=3,
                trans_fat=0, carbohydrates=60, sugar=8, sodium=700,
            )

        diary_a = _make_diary('壽司')
        diary_b = _make_diary('拉麵')

        def _make_analysis(diary, score):
            return AIAnalysis.objects.create(
                user=user, diary_entry=diary,
                prompt_sent='test', raw_response='{}',
                summary='test', status=AIAnalysis.StatusChoices.COMPLETED,
                ai_model_used='openai:gpt-4o-mini',
                nutrition_score=score,
            )

        analysis_a = _make_analysis(diary_a, score=80)
        analysis_b = _make_analysis(diary_b, score=60)

        response = self.client.get(MY_ANALYSES_URL)
        assert response.status_code == 200
        assert len(response.data) == 2
        # 最新的應排在第一位
        assert response.data[0]['nutrition_score'] == 60  # analysis_b 後建立

    def test_only_returns_own_analyses(self, db, ai_analysis):
        """不能看到其他使用者的分析結果（資料隔離）"""
        other_user = User.objects.create_user(
            username='another_user', password='Test1234!'
        )
        other_diary = DiaryEntry.objects.create(
            user=other_user,
            date=date.today(),
            meal_type='breakfast',
            food_name='土司',
            status=DiaryEntry.StatusChoices.COMPLETED,
            calories=200, protein=8, fat=4,
            saturated_fat=1, trans_fat=0,
            carbohydrates=35, sugar=5, sodium=300,
        )
        AIAnalysis.objects.create(
            user=other_user,
            diary_entry=other_diary,
            prompt_sent='test', raw_response='{}',
            summary='other user analysis',
            status=AIAnalysis.StatusChoices.COMPLETED,
            ai_model_used='gemini:gemini-2.5-flash',
        )

        response = self.client.get(MY_ANALYSES_URL)
        assert response.status_code == 200
        assert len(response.data) == 1  # 只能看到自己的那一筆

    def test_response_includes_required_fields(self, ai_analysis):
        response = self.client.get(MY_ANALYSES_URL)
        assert response.status_code == 200
        result = response.data[0]
        for field in ['id', 'diary_entry', 'summary', 'nutrition_score',
                      'exceeded_nutrients', 'lacking_nutrients',
                      'suggestions', 'status', 'ai_model_used', 'created_at']:
            assert field in result, f"Missing field: {field}"

    def test_returns_401_when_unauthenticated(self):
        response = APIClient().get(MY_ANALYSES_URL)
        assert response.status_code == 401