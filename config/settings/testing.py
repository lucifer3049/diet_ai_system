from .base import *  # noqa

DEBUG = False

# CI 測試用 SQLite，不需要 PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# 測試時關閉 AI 呼叫（用假的 key）
OPENAI_API_KEY = 'test-key'
GEMINI_API_KEY = 'test-key'
AI_PROVIDER = 'mock'

# 加快密碼雜湊速度（測試用）
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]