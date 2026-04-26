import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import DiaryEntry
from .serializers import DiaryEntrySerializer

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="日記列表"),
    create=extend_schema(summary="新增飲食日記(自動觸發AI分析)"),
    retrieve=extend_schema(summary="取得單一飲食日記"),
    partial_update=extend_schema(summary="更新飲食日記"),
    destroy=extend_schema(summary="刪除日記"),
)

@extend_schema(tags=["飲食日記"])
class DiaryEntryViewSet(viewsets.ModelViewSet):
    serializer_class = DiaryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return DiaryEntry.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        diary_entry = serializer.save(user=self.request.user)
        self._trigger_ai_analysis(diary_entry)
        
    def _trigger_ai_analysis(self, diary_entry: DiaryEntry):
        """
        建立日記後自動呼叫AI分析
        """

        from ai_analysis.services import get_ai_service
        from ai_analysis.models import AIAnalysis

        user = diary_entry.user
        provider = user.preferred_ai_provider

        try:
            service = get_ai_service(provider)

            # AI 分析食物營養素
            nutrition_result = service.analyze_food_nutrition(
                food_name=diary_entry.food_name,
                portion_description=diary_entry.portion_description,
            )

            # 營養素存回日記
            diary_entry.calories = nutrition_result.calories
            diary_entry.protein = nutrition_result.protein
            diary_entry.fat = nutrition_result.fat
            diary_entry.saturated_fat = nutrition_result.saturated_fat
            diary_entry.trans_fat = nutrition_result.trans_fat
            diary_entry.carbohydrates = nutrition_result.carbohydrates
            diary_entry.sugar = nutrition_result.sugar
            diary_entry.sodium = nutrition_result.sodium
            diary_entry.status = DiaryEntry.StatusChoices.COMPLETED
            diary_entry.save()

            # 建立AI飲食建議
            diary_data = {
                'food_name': diary_entry.food_name,
                'portion_description': diary_entry.portion_description,
                'calories': diary_entry.calories,
                'protein': diary_entry.protein,
                'fat': diary_entry.fat,
                'saturated_fat': diary_entry.saturated_fat,
                'trans_fat': diary_entry.trans_fat,
                'carbohydrates': diary_entry.carbohydrates,
                'sugar': diary_entry.sugar,
                'sodium': diary_entry.sodium,
            }

            user_profile = {
                'gender': user.get_gender_display() if user.gender else '未提供',
                'age': user.age,
                'height': float(user.height) if user.height else None,
                'weight': float(user.weight) if user.weight else None,
                'bmi': user.bmi,
                'goal': user.get_goal_display()
            }

            daily_needs = user.daily_nutrition_needs or {}

            advice_result = service.give_dietary_advice(diary_data, user_profile, daily_needs)

            AIAnalysis.objects.create(
                user=user,
                diary_entry=diary_entry,
                prompt_sent=f"食物分析：{diary_entry.food_name}",
                raw_response=advice_result.raw_response,
                summary=advice_result.summary,
                suggestions=advice_result.next_meal_suggestions,
                exceeded_nutrients=advice_result.exceeded_nutrients,
                lacking_nutrients=advice_result.lacking_nutrients,
                nutrition_score=advice_result.nutrition_score,
                status=AIAnalysis.StatusChoices.COMPLETED,
                ai_model_used=f"{provider}:{service.model_name}",
            )
        except Exception as e:
            logger.error(f"AI 分析失敗，diary_id={diary_entry.id}，錯誤:{e}")
            diary_entry.status = DiaryEntry.StatusChoices.FAILED
            diary_entry.save(update_fields=['status'])




            