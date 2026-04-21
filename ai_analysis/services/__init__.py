from decouple import config
from .base import BaseAIService, AnalysisResult
from .openai_service import OpenAIService
from .gemini_service import GeminiService


def get_ai_service(provider: str = None) -> BaseAIService:
    """
    1. 直接傳入 provider 參數(最高優先)
    2. 環境變數 AI_PROVIDER (系統預設)

    Args:
        provider: 'openai' or 'gemini'，不傳則用環境變數
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

    return service_class()

__all__ = ['get_ai_service', 'BaseAIService', 'AnalysisResult']