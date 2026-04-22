from .base import *

# 正式環境

DEBUG = False

# 正式環境只允許你的真實 domain
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
]


# 安全性設定（上線必須開啟）
SECURE_BROWSER_XSS_FILTER = True        # 防 XSS 攻擊
SECURE_CONTENT_TYPE_NOSNIFF = True      # 防 MIME 嗅探
X_FRAME_OPTIONS = 'DENY'               # 防 Clickjacking


# 正式環境 log：只記錄 WARNING 以上，存到檔案
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'production.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',  # 正式環境只記錄警告和錯誤
            'propagate': False,
        },
        'ai_analysis': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}