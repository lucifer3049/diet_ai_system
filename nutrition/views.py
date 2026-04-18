from rest_framework import viewsets, permissions, filters
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Food
from .serializers import FoodSerializer

@extend_schema_view(
    list=extend_schema(
        summary="食物列表",
        description="取得所有食物資料。支援搜尋: ?search={search_keyword}",
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                description='搜尋食物名稱或分類',
                required=False,
            )
        ]
    ),
    create=extend_schema(summary="新增食物"),
    retrieve=extend_schema(summary="取得單一食物"),
    update=extend_schema(summary="完整更新食物"),
    partial_update=extend_schema(summary="部分更新食物"),
    destroy=extend_schema(summary="刪除食物"),
)

@extend_schema(tags=["食物資料庫"])
class FoodViewSet(viewsets.ModelViewSet):
    """
    ViewSet = 把 list/create/retrieve/update/destroy 全包在一起
    一個class處理所有CRUD，這樣就不用寫多個view
    """

    queryset = Food.objects.all()
    serializer_class = FoodSerializer
    permission_classes = [permissions.IsAuthenticated]

    # 搜尋功能
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']