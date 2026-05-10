from .base import *  # noqa

DEBUG = False

# Celery 測試模式:

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

# 測試時 Celery 不用 Redis，同步執行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True