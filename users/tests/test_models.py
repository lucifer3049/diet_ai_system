import pytest
from datetime import date
from django.contrib.auth import get_user_model
from freezegun import freeze_time

User = get_user_model()

@pytest.mark.django_db
class TestUserBMI:
    def test_bmi_calculated_correctly(self):
        user = User(height=175, weight=70)
        assert user.bmi == pytest.approx(22.9, abs=0.1)

    def test_bmi_returns_none_when_height_missing(self):
        user = User(weight=70)
        assert user.bmi is None

    def test_bmi_returns_none_when_weight_missing(self):
        user = User(height=175)
        assert user.bmi is None


@pytest.mark.django_db
class TestUserAge:
    @freeze_time("2026-05-06")
    def test_age_calculated_correctly(self):
        user = User(birth_date=date(1990, 1, 1))
        assert user.age == 36

    @freeze_time("2026-05-06")
    def test_age_before_birthday_this_year(self):
        """生日還沒到，年齡應該少一歲"""
        user = User(birth_date=date(1990, 12, 31))
        assert user.age == 35

    def test_age_returns_none_without_birth_date(self):
        user = User()
        assert user.age is None


@pytest.mark.django_db
class TestDailyNutritionNeeds:
    def test_returns_none_when_profile_incomplete(self, user):
        user.birth_date = None
        assert user.daily_nutrition_needs is None

    def test_lose_weight_reduces_calories(self, user):
        from datetime import date
        user.birth_date = date(1990, 1, 1)
        user.goal = 'lose_weight'
        needs = user.daily_nutrition_needs
        
        user.goal = 'maintain'
        maintain_needs = user.daily_nutrition_needs
        
        assert needs['calories'] < maintain_needs['calories']
        assert needs['calories'] == maintain_needs['calories'] - 500

    def test_sodium_always_2300mg(self, user):
        from datetime import date
        user.birth_date = date(1990, 1, 1)
        needs = user.daily_nutrition_needs
        assert needs['sodium'] == 2300