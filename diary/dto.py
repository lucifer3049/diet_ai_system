from dataclasses import dataclass, asdict
from decimal import Decimal
from .models import DiaryEntry

@dataclass(frozen=True)
class DiaryNutritionDTO:
    food_name: str
    portion_description: str
    meal_type: str
    calories: float
    protein: float
    fat: float
    saturated_fat: float
    trans_fat: float
    carbohydrates: float
    sugar: float
    sodium: float

    @classmethod
    def from_entry(cls, entry: DiaryEntry) -> "DiaryNutritionDTO":
        return cls(
            food_name=entry.food_name,
            portion_description=entry.portion_description,
            meal_type=entry.get_meal_type_display(),
            calories=float(entry.calories or 0),
            protein=float(entry.protein or 0),
            fat=float(entry.fat or 0),
            saturated_fat=float(entry.saturated_fat or 0),
            trans_fat=float(entry.trans_fat or 0),
            carbohydrates=float(entry.carbohydrates or 0),
            sugar=float(entry.sugar or 0),
            sodium=float(entry.sodium or 0),
        )
    
    def to_dict(self) -> dict:
        return asdict(self)
    
