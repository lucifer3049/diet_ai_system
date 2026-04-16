from rest_framework import viewsets, permissions, filters
from .models import Food
from .serializers import FoodSerializer

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