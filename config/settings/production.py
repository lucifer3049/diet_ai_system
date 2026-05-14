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
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}