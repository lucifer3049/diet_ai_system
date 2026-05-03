FROM python:3.12.4-slim

# PYTHONDONTWRITEBYTECODE 不產生 .pyc 檔案
# PYTHONDONTWRITEBYTECODE 讓print/log 即時顯示
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 設定工作目錄，之後所有指令都在這個目錄裡面執行
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
# 複製 requirements.txt 到容器中
# Docker 有快取機制:這層沒變就不會重新執行
# 套件沒更新的話，下次 build 直接跳過這步驟，節省時間
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 複製專案的所有檔案到容器中
COPY . .

# 建立log資料夾
RUN mkdir -p logs

# 預設開發環境
# development 測試開發環境
# production 正式環境
ENV DJANGO_SETTINGS_MODULE=config.settings.development

# Django的預設埠
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]