import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from datetime import date

User = get_user_model()

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'Test1234!')
    height = 175
    weight = 70
    gender = 'male'
    preferred_ai_provider = 'gemini'

    class Params:
        # 有完整健康資料的使用者（可計算 BMI、daily_nutrition_needs）
        with_profile = factory.Trait(
            birth_date=date(1990, 1, 1),
            height=175,
            weight=70,
            gender='male',
        )
        lose_weight = factory.Trait(
            goal='lose_weight',
        )
        gain_muscle = factory.Trait(
            goal='gain_muscle',
        )
        gemini_user = factory.Trait(
            preferred_ai_provider='gemini',
        )
    
