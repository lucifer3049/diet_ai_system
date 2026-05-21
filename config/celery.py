import os
from celery import Celery

# 設定Django使用哪個 Django 設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('diet_ai_system')

# Django 設定 讀取 Celery 設定
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動發現每個 app 的 tasks.py
app.autodiscover_tasks()