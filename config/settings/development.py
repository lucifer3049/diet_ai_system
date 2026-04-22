from .base import * 

# * = 把base的設定都匯入
# noqa = 告訴 linter 忽略這行警告 

# 開發環境設定

DEBUG = True

# 開發時允許所有前端來源
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]

# 開發環境：詳細 log，方便 debug
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # 詳細格式：等級 時間 模組 訊息
        'verbose': {
            'format': '[{levelname}] {asctime} {module} | {message}',
            'style': '{',
        },
        # 簡單格式：只有訊息（給 console 用）
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        # 輸出到 terminal
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # 輸出到檔案（AI 相關 log 特別記錄）
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        # Django 本身的 log
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # 自己的 apps
        'users': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'diary': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ai_analysis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}