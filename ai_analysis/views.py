import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404

from diary.models import DiaryEntry
from .models import AIAnalysis
from .serializers import AIAnalysisSerializer
from .services import get_ai_service

logger = logging.getLogger(__name__)

class AnalyzeDiaryView(APIView):
    """
    POST /api/ai/analyze/{diary_id}/
    針對單獨一筆飲食日記，呼叫AI進行分析
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['AI 分析'],
        summary="分析飲食日誌",
        description="針對指定日誌呼叫 AI 進行營養分析，結果會存入資料庫。若已有分析結果，直接回傳不重複呼叫 AI。",
        responses={
            200: AIAnalysisSerializer,
            404: OpenApiResponse(description="找不到該筆資料"),
            500: OpenApiResponse(description="AI 分析失敗"),
        }
    )

    def post(self, request, diary_id):
        diary_entry = get_object_or_404(
            DiaryEntry,
            id=diary_id,
            user=request.user
        )

        # 避免重複分析
        if hasattr(diary_entry, 'ai_analysis'):
            logger.info(f"日誌 {diary_id} 已有分析結果，不重複呼叫AI。")
            serializer = AIAnalysisSerializer(diary_entry.ai_analysis)
            return Response(serializer.data)
        
        # 三層優先順序:
        # 1. Request body 指定 (最高優先)
        # 2. 使用者偏好設定
        # 3. 環境變數預設
        provider = (
            request.data.get('provider') or  # 前端這次請求指定
            request.user.preferred_ai_provider # 使用者偏好AI
        )

        # AI的資料
        diary_data = {
            'date': str(diary_entry.date),
            'meal_type': diary_entry.meal_type,
            'total_calories': float(diary_entry.total_calories),
            'total_protein': float(diary_entry.total_protein),
            'total_carbs': float(diary_entry.total_carbs),
            'total_fat': float(diary_entry.total_fat),
            'foods':[
                {
                    'food_name': df.food.name,
                    'amount_g': float(df.amount_g),
                }
                for df in diary_entry.diary_foods.all()
            ]

        }

        user = request.user
        user_data = {
            'height': float(user.height) if user.height else None,
            'weight': float(user.weight) if user.weight else None,
            'bmi': user.bmi,
            'goal': user.get_goal_display(),
            'daily_calorie_target': user.daily_calorie_target,
        }

        try:
            # 呼叫AI Service
            service = get_ai_service(provider)
            result = service.analyze_diet(diary_data, user_data)

            analysis = AIAnalysis.objects.create(
                user=request.user,
                diary_entry=diary_entry,
                prompt_sent=service._build_prompt(diary_data, user_data),
                raw_response=result.raw_response,
                summary=result.summary,
                suggestions=result.suggestions,
                nutrition_score=result.nutrition_score,
                status=AIAnalysis.StatusChoices.COMPLETED,
                ai_model_used=f"{provider}:{getattr(service, 'model_name', 'unknown')}",
            )

            return Response(AIAnalysisSerializer(analysis).data, 
                            status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"AI 分析失敗，diary_id={diary_id}，錯誤:{e}")

            return Response({"error": "AI 分析失敗，請稍後再試。"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
        analyses = AIAnalysis.objects.filter(user=request.user).order_by('-created_at')
        serializer = AIAnalysisSerializer(analyses, many=True)
        return Response(serializer.data)
