import factory
from factory.django import DjangoModelFactory
from nutrition.models import Food, FoodNutritionCache


class FoodFactory(DjangoModelFactory):
    class Meta:
        model = Food

    name = factory.Sequence(lambda n: f'食物_{n}')
    category = 'grain'
    calories_per_100g = 130
    protein_per_100g = 2.7
    carbs_per_100g = 28
    fat_per_100g = 0.3
    fiber_per_100g = 0

    class Params:
        protein_food = factory.Trait(
            name='雞胸肉',
            category='protein',
            calories_per_100g=165,
            protein_per_100g=31,
            carbs_per_100g=0,
            fat_per_100g=3.6,
        )
        vegetable = factory.Trait(
            category='vegetable',
            calories_per_100g=34,
        )


class FoodNutritionCacheFactory(DjangoModelFactory):
    class Meta:
        model = FoodNutritionCache

    food_name = factory.Sequence(lambda n: f'快取食物_{n}')
    calories = 550
    protein = 30
    fat = 20
    saturated_fat = 5
    trans_fat = 0.1
    carbohydrates = 60
    sugar = 10
    sodium = 800
    food_description = factory.LazyAttribute(lambda obj: f'{obj.food_name} 的描述')
    ai_model_used = 'gemini-2.0-flash'
    hit_count = 0
