import factory
from factory.django import DjangoModelFactory
from datetime import date
from diary.models import DiaryEntry
from users.tests.factories import UserFactory


class DiaryEntryFactory(DjangoModelFactory):
    class Meta:
        model = DiaryEntry

    user = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(date.today)
    meal_type = 'lunch'
    food_name = factory.Sequence(lambda n: f'食物_{n}')
    portion_description = '一份'
    status = DiaryEntry.StatusChoices.PENDING

    class Params:
        completed = factory.Trait(
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
        failed = factory.Trait(
            status=DiaryEntry.StatusChoices.FAILED,
        )
        processing = factory.Trait(
            status=DiaryEntry.StatusChoices.PROCESSING,
        )
