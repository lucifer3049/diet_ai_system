import pytest
from datetime import date
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()                        
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='Test1234!',
        height=175,
        weight=70,
        gender='male',
    )

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def completed_diary(user):
    from diary.models import DiaryEntry
    return DiaryEntry.objects.create(
        user=user,
        date=date.today(),
        meal_type='lunch',
        food_name='雞腿便當',
        portion_description='一個',
        status=DiaryEntry.StatusChoices.COMPLETED,
        calories=550,
        protein=30,
        fat=20,
        saturated_fat=5,
        trans_fat=0.1,
        carbohydrates=60,
        sugar=10,
        sodium=800,
    )

@pytest.fixture
def pending_diary(user):
    from diary.models import DiaryEntry
    return DiaryEntry.objects.create(
        user=user,
        date=date.today(),
        meal_type='lunch',
        food_name='雞腿便當',
        status=DiaryEntry.StatusChoices.PENDING,
    )

@pytest.fixture
def failed_diary(user):
    from diary.models import DiaryEntry
    return DiaryEntry.objects.create(
        user=user,
        date=date.today(),
        meal_type='lunch',
        food_name='雞腿便當',
        status=DiaryEntry.StatusChoices.FAILED,
    )

@pytest.fixture
def ai_analysis(user, completed_diary):
    from ai_analysis.models import AIAnalysis
    return AIAnalysis.objects.create(
        user=user,
        diary_entry=completed_diary,
        prompt_sent='food: 雞腿便當',
        raw_response='{"summary": "test"}',
        summary='這餐整體營養均衡，蛋白質攝取充足。',
        suggestions=['建議下一餐多補充蔬菜', '可以減少精緻澱粉'],
        exceeded_nutrients=['鈉'],
        lacking_nutrients=['膳食纖維'],
        nutrition_score=75,
        status=AIAnalysis.StatusChoices.COMPLETED,
        ai_model_used='openai:gpt-4o-mini',
    )

@pytest.fixture
def food_factory(db):
    from nutrition.models import Food

    def _create(name='白米飯', category='grain', calories=130,
                protein=2.7, carbs=28, fat=0.3):
        return Food.objects.create(
            name=name,
            category=category,
            calories_per_100g=calories,
            protein_per_100g=protein,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
        )
    return _create