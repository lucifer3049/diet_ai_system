import logging
from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import DiaryEntry
from .serializers import DiaryEntrySerializer
from .tasks import analyze_diary_entry_task


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

        # 非同步:丟給 Celery，立刻回傳，不用等待分析完成
        analyze_diary_entry_task.delay(diary_entry.id)
        logger.info(f"已排程 AI 分析，diary_id={diary_entry.id}")
