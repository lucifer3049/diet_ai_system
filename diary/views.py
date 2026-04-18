from django.shortcuts import get_list_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .models import DiaryEntry, DiaryFood
from .serializers import DiaryEntrySerializer, AddFoodToDiarySerializer
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

    def get_queryset(self):
        """
        使用者只能看到自己的資料
        這是資料隔離的部分
        """
        return DiaryEntry.objects.filter(user=self.request.user).prefetch_related('diary_foods__food') # prefetch_related 減少資料庫查詢次數，提高效率一次抓好
    
    def perform_create(self, serializer):
        """
        建立時，自動帶入使用者
        """
        serializer.save(user=self.request.user)

    @extend_schema(
            summary="新增食物到日記",
            description="指定食物ID和克數，新增這筆日記中。系統會自動重新計算營養總和。",
            request=AddFoodToDiarySerializer,
            responses={
                200: DiaryEntrySerializer,
                400: OpenApiResponse(description="food_id 或 amount_g 格式錯誤"),
                404: OpenApiResponse(description="找不到指定食物"),
            }
    )

    @action(detail=True, methods=['post'], url_path='add-food')
    def add_food(self, request, pk=None):
        """
        Post /api/diary/{id}/add-food/ -> API路徑
        @action : 自定義API端點
        detail=True : API路徑會帶入{id}參數，但須設定pk，反之False就不會帶入{id}
        - POST /api/diary/{id}/add-food/ -> True
        - POST /api/diary/add-food/ -> False
        """
        diary_entry = self.get_object() # 拿到食物日誌資料

        serializer = AddFoodToDiarySerializer(data=request.data) # 驗證資料
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        food = get_list_or_404(Food, id=serializer.validated_data['food_id']) 

        DiaryFood.objects.create(
            diary_entry=diary_entry,
            food=food,
            amount_g=serializer.validated_data['amount_g']
        )

        # 重新計算營養總和
        diary_entry.calculate_totals()

        return Response(
            DiaryEntrySerializer(diary_entry).data,
            status=status.HTTP_200_OK
        )
