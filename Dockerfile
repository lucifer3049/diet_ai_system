FROM python:3.12.4-slim

# 基本環境設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 設定工作目錄
WORKDIR /app

# apt-get update 更新Linux套件
# apt-get install -y 安裝必要的套件
# gcc: 用於編譯C擴展
# libpq-dev: PostgreSQL的開發套件
# curl: 發HTTP請求工具
# rm -rf /var/lib/apt/lists/*: 清除apt-get的緩存，減少映像檔大小
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 預設開發環境
# development 測試開發環境
# production 正式環境
ENV DJANGO_SETTINGS_MODULE=config.settings.development

# Django的預設埠
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]