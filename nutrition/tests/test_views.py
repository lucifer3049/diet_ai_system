"""
測試 FoodViewSet 的所有 CRUD 操作與搜尋功能：
- 列表查詢、關鍵字搜尋
- 建立、讀取、更新、刪除
- 權限控制（未認證應被拒絕）
"""
import pytest
from rest_framework.test import APIClient
from nutrition.models import Food

@pytest.fixture
def sample_foods(db):
    """建立三筆不同類別的食物測試資料"""
    Food.objects.create(
        name='白米飯', category='grain',
        calories_per_100g=130, protein_per_100g=2.7,
        carbs_per_100g=28, fat_per_100g=0.3,
    )
    Food.objects.create(
        name='雞胸肉', category='protein',
        calories_per_100g=165, protein_per_100g=31,
        carbs_per_100g=0, fat_per_100g=3.6,
    )
    Food.objects.create(
        name='花椰菜', category='vegetable',
        calories_per_100g=34, protein_per_100g=2.8,
        carbs_per_100g=7, fat_per_100g=0.4,
    )


@pytest.fixture
def single_food(db):
    return Food.objects.create(
        name='燕麥', category='grain',
        calories_per_100g=389, protein_per_100g=17,
        carbs_per_100g=66, fat_per_100g=7,
    )


VALID_PAYLOAD = {
    'name': '糙米飯',
    'category': 'grain',
    'calories_per_100g': '111.00',
    'protein_per_100g': '2.60',
    'carbs_per_100g': '23.00',
    'fat_per_100g': '0.90',
}

@pytest.mark.django_db
class TestFoodListView:
    URL = '/api/v1/foods/'

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        self.client = authenticated_client

    def test_returns_all_foods(self, sample_foods):
        response = self.client.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 3

    def test_response_includes_pagination_fields(self, sample_foods):
        response = self.client.get(self.URL)
        assert 'count' in response.data
        assert 'results' in response.data
        assert 'next' in response.data

    def test_search_by_exact_name(self, sample_foods):
        response = self.client.get(self.URL, {'search': '雞胸肉'})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['name'] == '雞胸肉'

    def test_search_by_partial_name(self, sample_foods):
        response = self.client.get(self.URL, {'search': '飯'})
        assert response.status_code == 200
        # 白米飯 應被找到
        assert response.data['count'] >= 1

    def test_search_by_category(self, sample_foods):
        response = self.client.get(self.URL, {'search': 'grain'})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['category'] == 'grain'

    def test_search_no_results_returns_empty(self, sample_foods):
        response = self.client.get(self.URL, {'search': '不存在的神秘食物XYZ'})
        assert response.status_code == 200
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_unauthenticated_returns_401(self):
        response = APIClient().get(self.URL)
        assert response.status_code == 401

    def test_empty_db_returns_empty_list(self):
        response = self.client.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 0


@pytest.mark.django_db
class TestFoodCreate:
    URL = '/api/v1/foods/'

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        self.client = authenticated_client

    def test_create_success(self):
        response = self.client.post(self.URL, VALID_PAYLOAD)
        assert response.status_code == 201
        assert response.data['name'] == '糙米飯'
        assert response.data['category'] == 'grain'
        assert Food.objects.filter(name='糙米飯').exists()

    def test_create_returns_id_and_created_at(self):
        response = self.client.post(self.URL, VALID_PAYLOAD)
        assert response.status_code == 201
        assert 'id' in response.data
        assert 'created_at' in response.data

    def test_create_missing_required_field_returns_400(self):
        payload = VALID_PAYLOAD.copy()
        del payload['calories_per_100g']
        response = self.client.post(self.URL, payload)
        assert response.status_code == 400

    def test_create_missing_name_returns_400(self):
        payload = VALID_PAYLOAD.copy()
        del payload['name']
        response = self.client.post(self.URL, payload)
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self):
        response = APIClient().post(self.URL, VALID_PAYLOAD)
        assert response.status_code == 401


@pytest.mark.django_db
class TestFoodRetrieve:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        self.client = authenticated_client

    def _url(self, food_id):
        return f'/api/v1/foods/{food_id}/'

    def test_retrieve_existing_food(self, single_food):
        response = self.client.get(self._url(single_food.id))
        assert response.status_code == 200
        assert response.data['name'] == '燕麥'
        assert float(response.data['calories_per_100g']) == 389.0

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(self._url(99999))
        assert response.status_code == 404

    def test_retrieve_includes_all_nutrition_fields(self, single_food):
        response = self.client.get(self._url(single_food.id))
        expected_fields = [
            'id', 'name', 'category',
            'calories_per_100g', 'protein_per_100g',
            'carbs_per_100g', 'fat_per_100g', 'created_at',
        ]
        for field in expected_fields:
            assert field in response.data, f"Missing field: {field}"


@pytest.mark.django_db
class TestFoodUpdate:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        self.client = authenticated_client

    def _url(self, food_id):
        return f'/api/v1/foods/{food_id}/'

    def test_partial_update_single_field(self, single_food):
        response = self.client.patch(self._url(single_food.id), {'calories_per_100g': '370.00'})
        assert response.status_code == 200
        single_food.refresh_from_db()
        assert float(single_food.calories_per_100g) == 370.0

    def test_partial_update_name(self, single_food):
        response = self.client.patch(self._url(single_food.id), {'name': '即食燕麥'})
        assert response.status_code == 200
        single_food.refresh_from_db()
        assert single_food.name == '即食燕麥'

    def test_full_update(self, single_food):
        payload = {
            'name': '大麥', 'category': 'grain',
            'calories_per_100g': '354.00',
            'protein_per_100g': '12.50',
            'carbs_per_100g': '73.00',
            'fat_per_100g': '2.30',
        }
        response = self.client.put(self._url(single_food.id), payload)
        assert response.status_code == 200
        assert response.data['name'] == '大麥'

    def test_update_nonexistent_returns_404(self):
        response = self.client.patch(self._url(99999), {'name': '不存在'})
        assert response.status_code == 404


@pytest.mark.django_db
class TestFoodDelete:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        self.client = authenticated_client

    def _url(self, food_id):
        return f'/api/v1/foods/{food_id}/'

    def test_delete_existing_food(self, single_food):
        food_id = single_food.id
        response = self.client.delete(self._url(food_id))
        assert response.status_code == 204
        assert not Food.objects.filter(id=food_id).exists()

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete(self._url(99999))
        assert response.status_code == 404

    def test_unauthenticated_returns_401(self, single_food):
        response = APIClient().delete(self._url(single_food.id))
        assert response.status_code == 401
        # 確認資料未被刪除
        assert Food.objects.filter(id=single_food.id).exists()
        