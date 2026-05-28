import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404

from diary.models import DiaryEntry
from .models import AIAnalysis
from .serializers import AIAnalysisSerializer
from .tasks import reanalyze_diary_task
from .analysis_service import  DiaryNotReadyError

logger = logging.getLogger(__name__)

class AnalyzeDiaryView(APIView):
    """
    HTTP層
    1. 確認 diary 存在且屬於此使用者
    2. 觸發非同步task
    3.回傳HTTP response
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['AI 分析'],
        summary="分析飲食日誌",
        description="非同步觸發 AI 飲食建議分析，立即回傳 202。若已有分析結果則直接回傳 200",
        responses={
            200: AIAnalysisSerializer,
            400: OpenApiResponse(description="日記尚未準備好"),
            404: OpenApiResponse(description="找不到該筆資料"),
            500: OpenApiResponse(description="AI 分析失敗"),
        }
    )

    def post(self, request, diary_id):
        diary_entry = get_object_or_404(
            DiaryEntry.objects.select_related('ai_analysis'),
            id=diary_id,
            user=request.user
        )

        # 已有結果值截回傳，不需要進task
        try:
            analysis = diary_entry.ai_analysis
            return Response(AIAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)
        except DiaryEntry.ai_analysis.RelatedObjectDoesNotExist:
            pass

        # 只有 COMPLETED（且無 ai_analysis）才允許觸發建議分析；其餘狀態都不行
        non_ready_statuses = {
            DiaryEntry.StatusChoices.PENDING: "營養成分分析尚未完成，請稍後再試",
            DiaryEntry.StatusChoices.PROCESSING: "目前正在分析中，請稍後再試",
            DiaryEntry.StatusChoices.FAILED: "日誌的營養成分分析失敗，無法給予飲食建議。",
        }
        if diary_entry.status in non_ready_statuses:
            return Response({"error": non_ready_statuses[diary_entry.status]}, status=status.HTTP_400_BAD_REQUEST)
        

        # 三層優先順序:
        # 1. Request body 指定 (最高優先)
        # 2. 使用者偏好設定
        # 3. 環境變數預設
        provider = (
            request.data.get('provider') or  # 前端這次請求指定
            request.user.preferred_ai_provider # 使用者偏好AI
        )
        #
        reanalyze_diary_task.delay(diary_entry.id, provider)
        logger.info(f"已排程飲食建議分析，diary_id={diary_id}")

        return Response({"message":"分析已排程，請稍後查詢 GET /api/v1/ai/my-analyses/"}, status=status.HTTP_202_ACCEPTED)
        
class MyAnalysisListView(APIView):
    """
    GET /api/ai/my-analyses/
    取得我所有AI分析的紀錄
    """

    permission_classes = [IsAuthenticated] # 使用者必須登入才能取得自己的資料

    @extend_schema(
        tags=['AI 分析'],
        summary="取得我的分析紀錄",
        responses={200: AIAnalysisSerializer(many=True)}
    )
    def get(self, request):
        # 以 -id 當 tie-breaker：created_at 並列時（同一微秒，Windows 時鐘粒度粗時常見）
        # 仍有穩定且正確的順序，避免列表/分頁順序不確定。
        analyses = (
            AIAnalysis.objects.filter(user=request.user)
            .select_related('diary_entry')
            .order_by('-created_at', '-id')
        )
        
        return Response(AIAnalysisSerializer(analyses, many=True).data)
