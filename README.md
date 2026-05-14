# 飲食控制AI系統
一個Django REST API後端系統，整合OpenAI和Gemini AI，使用者輸入食物名稱，系統自動分析營養素並提供個人化飲食建議，採用Celery非同步處理AI任務，Docker容器化部屬，GitHub Actions CI/CD自動化流程

---

## 專案目標

本專案目的是建立一個完整的：

- 飲食紀錄系統
- AI 自動營養分析
- 個人化飲食建議
- 每日營養需求計算
- 高效能 API 後端架構

---

## 功能

# 使用者系統
- JWT 註冊 / 登入驗證
- 個人健康資料管理
- BMI 自動計算
- 每日營養需求分析

# AI 營養分析
- 輸入食物名稱，自動分析營養素
- 支援 OpenAI / Gemini 動態切換
- AI 營養師建議
  - 熱量是否過高
  - 營養素攝取不足
  - 下一餐建議
- 食物營養快取（避免重複 AI 呼叫）

# 飲食日記系統
- 新增 / 修改 / 刪除飲食紀錄
- 自動觸發 AI 分析
- 個人飲食歷史查詢

# API 文件
- Swagger UI
- ReDoc
- OpenAPI 3.0 自動生成

---

## Docker 常用指令
```bash
docker compose up --build   # 第一次啟動
docker compose up -d        # 背景執行
docker compose down         # 停止
docker compose down -v      # 停止並清空資料庫
docker compose logs -f web  # 查看 log
docker compose ps           # 查看容器狀態
docker compose exec web bash # 進入容器
docker compose exec web sh # 檢查有沒有bash

# 容器內執行 Django 指令
docker compose exec web python manage.py migrate  # 更新模組
docker compose exec web python manage.py createsuperuser # 建立管理者權限
docker compose exec web pytest # 執行測試文件
```

# 快速開始

```bash
# 1. 複製環境變數
cp .env.example .env
# 填入 SECRET_KEY、DB 設定、AI API Key

# 2. 啟動所有服務
docker compose up --build

# 3. 建立管理員帳號
docker compose exec web python manage.py createsuperuser
```

打開 `http://localhost:8000/api/docs/` 查看 API 文件。

---

### 本機開發
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 
deactivate # 離開venv
```

## 環境變數說明
```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# PostgreSQL（Docker 環境 DB_HOST 填 db）
DB_NAME=diet_ai_system
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432

# AI（openai 或 gemini）
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.0-flash
```

## 技術棧

### 後端
- Python 3.12
- Django 
- Django REST Framework
- PostgreSQL
- JWT Authentication
- drf-spectacular（OpenAPI 3.0 自動文件）

### AI
- OpenAI API（GPT-4o-mini）
- Google Gemini API（Gemini 2.0 Flash）
- Factory Pattern(工廠模式)
- 抽象Service Interface

### DevOps
- Docker
- Docker Compose
- DockerHub
- GitHub Actions CI/CD

---

## 專案結構（規劃中）
```
diet-ai-system/
├── config/
│   ├── settings/
│   │   ├── base.py          # 共用設定
│   │   ├── development.py   # 開發環境
│   │   └── production.py    # 正式環境
│   ├── exceptions.py        # 統一錯誤格式
│   ├── urls.py
│   └── wsgi.py
├── users/                   # 使用者（註冊/登入/JWT/健康資料）
├── diary/                   # 飲食日記（CRUD + 自動 AI 分析）
├── nutrition/               # 食物資料庫 + 快取
├── ai_analysis/             # AI 分析結果
│   └── services/
│       ├── base.py          # 抽象介面 + 共用 Prompt
│       ├── openai_service.py
│       └── gemini_service.py
├── logs/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── manage.py
└── requirements.txt
```

# API 文件
- drf-spectacular (OpenAPI 3.0)
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`


## API 端點
```
AI分析
POST /api/v1/ai/analyze/{diary_id}/  分析飲食日誌
GET /api/v1/ai/my-analyses/          取得AI分析資料

認證
POST /api/v1/auth/register/       使用者註冊
POST /api/v1/auth/login/          登入取得 JWT Token
POST /api/v1/auth/token/refresh/  刷新 Token

使用者
GET  /api/v1/users/me/            取得個人資料（含 BMI、每日營養需求）
PATCH /api/v1/users/me/           更新個人資料

飲食日記
POST /api/v1/diary/               新增日記（自動觸發 AI 分析）
GET  /api/v1/diary/               我的日記列表
GET  /api/v1/diary/{id}/          單筆日記（含營養素）
PATCH /api/v1/diary/{id}/         更新日記
DELETE /api/v1/diary/{id}/        刪除日記

食物資料庫
GET  /api/v1/foods/               食物列表（支援搜尋）
POST /api/v1/foods/               新增食物
GET  /api/v1/foods/{id}/          取得單一食物
PUT /api/v1/foods/{id}/           完整更新食物
PATCH /api/v1/foods/{id}/         更新部分食物
DELETE /api/v1/foods/{id}/        刪除食物

```

## Django 自動化測試
pip install pytest pytest-django pytest-cov factory-boy faker freezegun 


## 開發進度

- [V] 第 1 階段：專案初始化 + Settings 環境分離
- [V] 第 2 階段：資料庫與 Models 設計
- [V] 第 3 階段：RESTful API（DRF）+ Swagger UI
- [V] 第 4 階段：AI Service Layer
  - [V] OpenAI / Gemini 雙模型支援
  - [V] 三層切換機制（Request > 使用者偏好 > 環境變數）
  - [V] 食物營養快取（FoodNutritionCache）
  - [V] Harris-Benedict 公式計算每日營養需求
- [V] 第 5 & 6 階段：Docker + Docker Compose
- [V] 第 7 階段：CI/CD（GitHub Actions）
- [] 第 8 階段: 測試 Testing

## 未來規劃

- [ ] Celery 非同步處理（AI 分析改背景執行）
- [ ] 圖片辨識（上傳食物照片自動識別）
- [ ] 每日 / 每週飲食趨勢分析
- [ ] React 前端(前後端分離) 或 Vue/Vite

## Docker Hub建立
```
# 建立本地 Docker 映像檔
docker build -t hoaquan/diet-ai-system:latest .

# 登入Docker Hub
docker login -u hoaquan

# 上傳到Docker Hub
docker push hoaquan/diet-ai-system:latest

# 驗證docker
docker images

```
