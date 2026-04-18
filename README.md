# 飲食控制AI系統

這是一個 AI 驅動的飲食管理系統，幫助使用者記錄飲食、分析營養，並提供智慧飲食建議，我的練習專案。

---

## 專案目標

本專案目的是建立一個完整的：

- 飲食紀錄系統
- 營養分析系統
- AI 飲食建議平台

---

## 功能

- 使用者註冊 / 登入（JWT）
- 飲食紀錄（CRUD）
- 營養分析（熱量 / 蛋白質 / 碳水 / 脂肪）
- AI 飲食建議（OpenAI / Gemini）
- API 文件 (Swagger UI / ReDoc)


---

# 環境設定

複製 `.env.example` 為 `.env` 並填入設定

```bash
cp .env.example .env
```

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

AI_PROVIDER=openai  # 改成 gemini 可切換
OPENAI_API_KEY=''
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=''
GEMINI_MODEL=gemini-1.5-flash
```
---

# 快速開始

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate 

venv\Scripts\activate # Windows 啟動虛擬機指令

# 安裝套件
pip install -r requirements.txt

# 資料庫 migration
python manage.py migrate

# 啟動開發伺服器
python manage.py runserver
```

# API文件
打開 `http://localhost:8000/api/docs/` 查看 API 文件。

---

## 技術棧

### 後端
- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- JWT 認證 (djangorestframework-simplejwt)

### AI
- OpenAI API
- Google Gemini API

### DevOps (規劃中)
- Docker
- Docker Compose
- GitHub Actions（CI/CD）

---

## 專案結構（規劃中）
```
diet-ai-system/
├── config/                  # Django 設定中心
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/                   # 使用者 app（註冊/登入/JWT）
├── diary/                   # 飲食日記 app（CRUD）
├── nutrition/               # 食物營養資料庫 app
├── ai_analysis/             # AI 分析 app（Service Layer）
│   └── services/
│       ├── base.py          # 抽象介面
│       ├── openai_service.py
│       └── gemini_service.py
├── docker/                  # Docker 設定（規劃中）
├── .env.example             # 環境變數範例
├── manage.py
└── requirements.txt
```

# API 文件
- drf-spectacular (OpenAPI 3.0)
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`


## API 端點
```
# 認證使用者
POST   /api/auth/register/          ← 註冊
POST   /api/auth/login/             ← 登入（取得 JWT token）
POST   /api/auth/token/refresh/     ← 刷新 token

# 使用者
GET    /api/users/me/               ← 取得自己的資料
PATCH  /api/users/me/               ← 更新自己的資料

# 食物資料庫（nutrition）
GET    /api/foods/                  ← 列出所有食物
POST   /api/foods/                  ← 新增食物
GET    /api/foods/{id}/             ← 取得單一食物
PATCH  /api/foods/{id}/             ← 更新食物
DELETE /api/foods/{id}/             ← 刪除食物

# 飲食日記（diary）
GET    /api/diary/                  ← 列出我的日記
POST   /api/diary/                  ← 新增一筆日記
GET    /api/diary/{id}/             ← 取得單一日記
PATCH  /api/diary/{id}/             ← 更新日記
DELETE /api/diary/{id}/             ← 刪除日記
POST   /api/diary/{id}/add-food/    ← 新增食物到日記

```



# 開發進度
- [V] 第 1 階段:專案初始化
- [V] 第 2 階段:資料庫與Models設計
- [V] 第 3 階段:RESTful API (DRF) + Swagger UI
- [] 第 4 階段:AI Service Layer
- [] 第 5 階段：Docker
- [] 第 6 階段：Django + Docker 整合
- [] 第 7 階段：CI/CD (GitGub Action)