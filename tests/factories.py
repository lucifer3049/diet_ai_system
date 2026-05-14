import factory
from factory.django import DjangoModelFactory
from datetime import date


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'user.User'

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'Test1234!')
    height = 175
    weight = 70
    gender = 'male'
    birth_date = date(1990, 1, 1)
    goal = 'maintain'
    preferred_ai_provider = 'gemini'

class DiaryEntryFactory(DjangoModelFactory):
    class Meta:
        model = 'diary.DiaryEntry'
    
    user = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(date.today)
    meal_type = 'lunch'
    food_name = factory.Sequence(lambda n: f'食物_{n}')
    status = 'completed'
    calories = 550
    protein = 30
    fat = 20
    saturated_fat = 5
    trans_fat = 0
    carbohydrates = 60
    sugar = 10
    sodium = 800

class DiaryEntryPendingFactory(DiaryEntryFactory):
    status = 'pending'
    calories = None
    protein = None
    fat = None
    saturated_fat = None
    trans_fat = None
    carbohydrates = None
    sugar = None
    sodium = None

class AIAnalysisFactory(DjangoModelFactory):
    class Meta:
        model = 'ai_analysis.AIAnalysis'

    user = factory.SubFactory(UserFactory)
    diary_entry = factory.SubFactory(DiaryEntryFactory, user=factory.SelfAttribute('..user'))
    prompt_sent = 'test prompt'
    raw_response = '{}'
    summary = '這餐整體營養均衡。'
    nutrition_score = 75
    status = 'completed'
    ai_model_used = 'gemini:gemini-2.0-flash'

class FoodFactory(DjangoModelFactory):
    class Meta:
        model = 'nutrition.Food'

    name = factory.Sequence(lambda n: f'食物_{n}')
    category = 'grain'
    calories_per_100g = 130
    protein_per_100g = 2.7
    carbs_per_100g = 28
    fat_per_100g = 0.3
