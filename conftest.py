import pytest
from datetime import date
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    from users.tests.factories import UserFactory
    return UserFactory(
        username='testuser',
        email='test@test.com',
        with_profile=True,
    )


@pytest.fixture
def other_user(db):
    from users.tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def completed_diary(user):
    from diary.tests.factories import DiaryEntryFactory
    return DiaryEntryFactory(user=user, completed=True, food_name='雞腿便當')


@pytest.fixture
def pending_diary(user):
    from diary.tests.factories import DiaryEntryFactory
    return DiaryEntryFactory(user=user, food_name='雞腿便當')


@pytest.fixture
def failed_diary(user):
    from diary.tests.factories import DiaryEntryFactory
    return DiaryEntryFactory(user=user, failed=True, food_name='雞腿便當')


@pytest.fixture
def ai_analysis(user, completed_diary):
    from ai_analysis.tests.factories import AIAnalysisFactory
    return AIAnalysisFactory(
        user=user,
        diary_entry=completed_diary,
        nutrition_score=75,
        summary='這餐整體營養均衡，蛋白質攝取充足。',
    )


@pytest.fixture
def food_cache(db):
    from nutrition.tests.factories import FoodNutritionCacheFactory
    return FoodNutritionCacheFactory(food_name='白米飯')

@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
    