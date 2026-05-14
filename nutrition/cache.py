from django.core.cache import cache
from dataclasses import asdict

FOOD_CACHE_PREFIX = 'food_nutrition:'
FOOD_CACHE_TTL = 60 * 60 * 24 * 7 # 7天後自動失效

def get_food_cache_key(food_name: str) -> str:
    return f"{FOOD_CACHE_PREFIX}{food_name.strip().lower()}"

def get_cached_nutrition(food_name: str) -> dict | None:
    return cache.get(get_food_cache_key(food_name))

def set_cached_nutrition(food_name: str, nutrition_data: dict) -> None:
    cache.set(get_food_cache_key(food_name), nutrition_data, FOOD_CACHE_TTL)
    