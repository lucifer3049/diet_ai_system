"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,  # 產生 schema 的核心 view
    SpectacularSwaggerView, # Swagger UI 介面
    SpectacularRedocView, # ReDoc 介面
)

# Django 整合Django DRF所有專案的URL路口
urlpatterns = [
    path('admin/', admin.site.urls),

    # API 文件
    # 這個端點產生原始 schema (JSON / YAML 格式)
    # 前端 / OpenAPI 串接
    # 機器 / 前端工具 / 自動化系統
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI (前端互動介面)
    # url_name='schema 讀取上面那個端點產生的schema
    # 開發者可以用這個端點進行測試
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 這個端點是 ReDoc 
    # API文件適合適合對外公開的文件
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # 內部API 
    path('api/v1/', include('users.urls')), 
    path('api/v1/', include('nutrition.urls')),
    path('api/v1/', include('diary.urls')),
    path('api/v1/', include('ai_analysis.urls')) # AI 路徑API
]
