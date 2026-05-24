from decouple import config
from .base import BaseAIService, NutritionAnalysisResult, DietaryAdviceResult
from .openai_service import OpenAIService
from .gemini_service import GeminiService


def get_ai_service(
    provider: str = None,
    api_key: str | None = None,
    model: str | None = None,
) -> BaseAIService:
    """
    優先順序：
    1. 傳入的 provider 參數
    2. 環境變數 AI_PROVIDER

    api_key / model 若不傳，各 service 內部會 fallback 到 .env 設定。
    """

    if provider is None:
        provider = config('AI_PROVIDER', default='openai')

    provider = provider.lower().strip()

    services = {
        'openai': OpenAIService,
        'gemini': GeminiService,
    }

    service_class = services.get(provider)
    if not service_class:
        raise ValueError(f"不支援的 AI provider: {provider}，可用選項: {list(services.keys())}")

    return service_class(api_key=api_key, model=model)


__all__ = ['get_ai_service', 'BaseAIService', 'NutritionAnalysisResult', 'DietaryAdviceResult']
