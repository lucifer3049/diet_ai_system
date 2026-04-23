from django.shortcuts import get_list_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .models import DiaryEntry
from .serializers import DiaryEntrySerializer
from nutrition.models import Food


@extend_schema_view(
    list=extend_schema(summary="日記列表"),
    create=extend_schema(summary="新增飲食日記"),
    retrieve=extend_schema(summary="取得單一飲食日記"),
    partial_update=extend_schema(summary="更新飲食日記"),
    destroy=extend_schema(summary="刪除日記")
)

@extend_schema(tags=["飲食日記"])
class DiaryEntryViewSet(viewsets.ModelViewSet):
    serializer_class = DiaryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return DiaryEntry.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
