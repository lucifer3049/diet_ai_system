# Diet AI System

> 結合 LLM 的個人化飲食追蹤後端系統。透過 Django REST Framework 提供 API，整合 OpenAI / Gemini 雙模型進行食物營養分析與飲食建議生成；採用 **三層快取機制** 降低 AI 呼叫成本，**Celery 非同步任務** 避免阻塞請求，並以 Service Layer 分層架構維持可測試性與可擴充性。

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)]()
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)]()
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)]()
[![Coverage](https://img.shields.io/badge/coverage-≥70%25-brightgreen)]()

---

## 目錄

- [專案動機與設計目標](#專案動機與設計目標)
- [系統架構](#系統架構)
- [核心設計決策](#核心設計決策)
- [技術棧](#技術棧)
- [專案結構](#專案結構)
- [快速開始](#快速開始)
- [API 概覽](#api-概覽)
- [測試策略](#測試策略)
- [CI/CD Pipeline](#cicd-pipeline)
- [未來規劃](#未來規劃)

---

## 專案動機與設計目標

直接每次呼叫 LLM 分析食物會造成：

- **成本爆炸**：相同食物（如「白米飯」）被反覆呼叫
- **延遲過高**：使用者新增日記時必須等待 3–5 秒
- **可靠性低**：第三方 API 限流或失敗會直接影響使用者體驗

本專案的工程目標是用 **多層快取 + 非同步處理 + 抽象化 Provider** 解決上述問題，同時維持可替換、可測試、可擴充的後端架構。

---

## 系統架構

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP + JWT
       ▼
┌─────────────────────────────────────────────────┐
│              Django REST Framework               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Views   │→ │ Service  │→ │   Models     │  │
│  │ (Thin)   │  │  Layer   │  │  (ORM)       │  │
│  └──────────┘  └────┬─────┘  └──────┬───────┘  │
└─────────────────────┼────────────────┼──────────┘
                      │                │
       ┌──────────────┼────────────────┼────────────┐
       │              ▼                ▼            │
       │      ┌──────────────┐  ┌────────────┐    │
       │      │  Celery      │  │ PostgreSQL │    │
       │      │  Worker      │  │  (L2 Cache)│    │
       │      └──────┬───────┘  └────────────┘    │
       │             │                              │
       │             ▼                              │
       │      ┌──────────────┐  ┌────────────┐    │
       │      │   Redis      │  │  AI APIs   │    │
       │      │ (L1 Cache +  │  │ OpenAI /   │    │
       │      │   Broker)    │  │  Gemini    │    │
       │      └──────────────┘  └────────────┘    │
       └──────────────────────────────────────────┘
```

### 三層快取架構（食物營養查詢）

```
食物名稱 ──▶ L1: Redis ──hit──▶ 回傳 (~ms 級)
              │ miss
              ▼
           L2: PostgreSQL ──hit──▶ 回填 L1 後回傳 (~10ms)
              │ miss            (同時 hit_count +1)
              ▼
           L3: AI API (OpenAI / Gemini) ──▶ 寫入 L1 + L2 (~3-5s)
```

實作位置：`diary/services.py` → `DiaryService.get_nutrition_from_cache_or_ai()`

### 請求生命週期（新增飲食日記）

```
POST /api/v1/diary/
    │
    ▼
[View] 驗證 + 建立 DiaryEntry (status=PENDING)
    │
    ├─有圖片──▶ analyze_diary_image_task.delay()  ──┐
    │                                                │
    └─無圖片──▶ analyze_diary_entry_task.delay()  ──┤
    │                                                │
    ▼                                                ▼
回傳 201 (不阻塞)                          [Celery Worker]
                                          ├─ L1/L2/L3 取營養
                                          ├─ 寫回 DiaryEntry
                                          ├─ AI 飲食建議
                                          └─ 寫入 AIAnalysis
                                          status: COMPLETED / FAILED
```

---

## 核心設計決策

### 1. Service Layer 分層架構

**問題**：Django 預設容易陷入 Fat View / Fat Model，導致業務邏輯散落、難以測試。

**做法**：

| 層級 | 職責 | 範例 |
|---|---|---|
| **View** | HTTP 處理、權限驗證、回傳 Response | `ai_analysis/views.py` |
| **Service** | 業務邏輯、跨模組協調、交易控制 | `diary/services.py` |
| **Model** | 資料結構與簡單 property（如 BMI） | `users/models.py` |
| **Serializer** | 僅做驗證與序列化，不放業務邏輯 | `diary/serializers.py` |

**效益**：Service 可以脫離 HTTP 層獨立測試，View 變得極薄（多數 < 30 行）。

### 2. AI Provider 抽象化（Strategy + Factory Pattern）

**問題**：OpenAI 與 Gemini 的 SDK 介面完全不同；若直接寫在業務邏輯內，未來新增 Provider（如 Claude、Llama）需要改多處程式碼。

**做法**：

```python
# ai_analysis/services/base.py
class BaseAIService(ABC):
    @abstractmethod
    def analyze_food_nutrition(...) -> NutritionAnalysisResult: ...
    @abstractmethod
    def give_dietary_advice(...) -> DietaryAdviceResult: ...
    @abstractmethod
    def _do_call_vision_api(...) -> str: ...

# ai_analysis/services/__init__.py
def get_ai_service(provider: str = None) -> BaseAIService:
    return {'openai': OpenAIService, 'gemini': GeminiService}[provider]()
```

- 共用 Prompt 組裝與 JSON 解析邏輯放 `BaseAIService`
- 各 Provider 只需實作 `_call_api` 與 `_do_call_vision_api`
- 回傳值用 `@dataclass` 強型別化（`NutritionAnalysisResult` / `DietaryAdviceResult`），避免 dict 亂飛

**新增 Provider 的成本**：僅需新增一支 service 檔 + 註冊到 factory。

### 3. AI Provider 三層優先順序

```
Request body (前端臨時指定)
       ↓ 若空
User.preferred_ai_provider (使用者偏好)
       ↓ 若空
config('AI_PROVIDER') (環境變數預設)
```

實作於 `ai_analysis/views.py::AnalyzeDiaryView.post()`，支援前端在不修改使用者偏好的前提下，臨時切換 Provider 做 A/B 比較。

### 4. Celery 非同步任務拆分

`analyze_diary_entry_task` 與 `analyze_diary_image_task` 拆成兩支獨立 task，原因：

- **不同 retry 策略**：圖片辨識失敗成本高，可獨立調整 `max_retries`
- **獨立 concurrency 控制**：Vision API 通常較慢且配額較少，需限流
- **獨立監控**：成功率、平均延遲可分開觀測

### 5. 圖片辨識的資料一致性保證

```python
# diary/services.py
with transaction.atomic():
    cls._save_components(...)      # bulk_create N 筆 DiaryComponent
    cls._aggregate_to_diary(...)    # 加總後寫回 DiaryEntry
```

- **`bulk_create`** 取代逐筆 INSERT：10 個食物成份 = 1 次 SQL，而非 10 次
- **`transaction.atomic`**：聚合失敗則 components 一併 rollback，避免「拆解了但沒加總」的中間狀態

### 6. 環境分離（base / development / production / testing）

| 環境 | 重點差異 |
|---|---|
| `base.py` | 共用 INSTALLED_APPS、DRF、JWT、Celery、Spectacular |
| `development.py` | DEBUG=True、verbose logging 到檔案、寬鬆 CORS |
| `production.py` | DEBUG=False、JSON formatted log、安全 header（XSS / Clickjacking） |
| `testing.py` | SQLite in-memory、`CELERY_TASK_ALWAYS_EAGER=True`、MD5 password hasher 加速 |

### 7. 統一錯誤回應格式

DRF 預設錯誤格式不一致（有時 `{"detail": ...}` 有時 `{"field": [...]}`）。透過 `config/exceptions.py` 統一包裝成：

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": { ... }
  }
}
```

### 8. 觀測性

- **健康檢查端點** `config/health.py`：檢查 DB + Redis 連線狀態，K8s readiness probe 可直接使用
- **結構化日誌**：production 環境輸出 JSON 格式，方便 ELK / Loki 收集
- **AI 呼叫全程記錄**：每次 Provider 呼叫前後都有 logger.info，便於排查成本與延遲

---

## 技術棧

### Backend
- **Python 3.12** / **Django 5.0** / **Django REST Framework 3.15**
- **PostgreSQL 15** — 主資料庫
- **Redis 7** — 快取 + Celery broker
- **Celery 5.4** — 非同步任務佇列
- **drf-spectacular** — OpenAPI 3.0 自動產生
- **SimpleJWT** — JWT 認證 + Token rotation + blacklist

### AI Integration
- **OpenAI API** (gpt-4o-mini / gpt-4o for Vision)
- **Google Gemini API** (gemini-2.5-flash)

### Testing
- **pytest** + **pytest-django** + **pytest-cov**（覆蓋率門檻 70%）
- **factory_boy** + **Faker** — 測試資料工廠
- **freezegun** — 時間相關邏輯測試（如 BMI、年齡計算）

### DevOps
- **Docker** + **Docker Compose** — 多服務編排（web / db / redis / celery / celery-beat）
- **GitHub Actions** — CI（測試 + Docker build 驗證）/ CD（push image to Docker Hub）
- **Gunicorn** + **Nginx**（production compose）

---

## 專案結構

```
diet-ai-system/
├── config/                      # 專案設定
│   ├── settings/
│   │   ├── base.py             # 共用設定
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── celery.py               # Celery app 初始化
│   ├── exceptions.py           # 統一錯誤格式
│   ├── health.py               # 健康檢查端點
│   └── urls.py
│
├── users/                       # 使用者與認證
│   ├── models.py               # User + BMI + Harris-Benedict
│   ├── serializers.py
│   ├── views.py                # Register / Login / Profile
│   └── tests/
│
├── nutrition/                   # 食物資料庫 + L2 快取
│   ├── models.py               # Food / FoodNutritionCache
│   ├── cache.py                # Redis L1 cache helpers
│   └── tests/
│
├── diary/                       # 飲食日記（核心 domain）
│   ├── models.py               # DiaryEntry / DiaryComponent
│   ├── services.py             # 三層快取 + AI 流程編排
│   ├── tasks.py                # Celery tasks
│   ├── views.py                # ViewSet (CRUD)
│   └── tests/                  # services / tasks / views 分層測試
│
├── ai_analysis/                 # AI 服務層
│   ├── services/
│   │   ├── base.py             # BaseAIService 抽象 + Prompt 組裝
│   │   ├── openai_service.py
│   │   ├── gemini_service.py
│   │   └── __init__.py         # Factory: get_ai_service()
│   ├── analysis_service.py     # 業務邏輯
│   ├── tasks.py                # 重新分析 task
│   ├── views.py
│   └── tests/
│
├── .github/workflows/
│   ├── ci.yml                  # test + docker build 驗證
│   └── cd.yml                  # push image to Docker Hub
│
├── conftest.py                  # pytest fixtures（user / diary / cache）
├── docker-compose.yml           # 開發環境
├── docker-compose.prod.yml      # 正式環境（含 nginx + gunicorn）
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

### 分層職責對照

| 元件 | 職責 | 不該做的事 |
|---|---|---|
| `views.py` | HTTP 解析、權限、回傳 Response | 業務邏輯、複雜查詢 |
| `services.py` | 業務流程、Cache 策略、Transaction 控制 | 直接回傳 DRF Response |
| `tasks.py` | Celery task 進入點、retry 策略 | 業務邏輯（委派給 service） |
| `serializers.py` | 驗證與序列化 | 跨模組協調 |
| `models.py` | 資料結構、property 計算 | I/O、外部呼叫 |

---

## 快速開始

### 環境需求
- Docker 20.10+
- Docker Compose v2

### 啟動

```bash
# 1. 複製環境變數
cp .env.example .env
# 填入 SECRET_KEY、DB_*、OPENAI_API_KEY / GEMINI_API_KEY

# 2. 啟動所有服務（web / db / redis / celery / celery-beat）
docker compose up --build

# 3. 建立管理員帳號
docker compose exec web python manage.py createsuperuser
```

開啟 http://localhost:8000/api/docs/ 查看 Swagger UI。

### 常用指令

```bash
# 進入容器
docker compose exec web bash

# 執行 migration
docker compose exec web python manage.py migrate

# 執行測試
docker compose exec web pytest

# 查看 Celery worker 日誌
docker compose logs -f celery

# 停止並清空資料（含 volume）
docker compose down -v
```

### 本機開發（不使用 Docker）

```bash
python -m venv venv
source venv/bin/activate              # Mac/Linux
venv\Scripts\activate                 # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 另開終端啟動 Celery worker
celery -A config worker --loglevel=info
```

---

## API 概覽

完整 OpenAPI schema：`/api/schema/` ｜ Swagger UI：`/api/docs/` ｜ ReDoc：`/api/redoc/`

### 認證

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/auth/register/` | 使用者註冊 |
| POST | `/api/v1/auth/login/` | 取得 JWT access + refresh token |
| POST | `/api/v1/auth/token/refresh/` | 用 refresh token 換新 access token |

### 使用者

| Method | Endpoint | 說明 |
|---|---|---|
| GET | `/api/v1/users/me/` | 取得個人資料（含 BMI、年齡、每日營養需求） |
| PATCH | `/api/v1/users/me/` | 更新身高、體重、目標、偏好 AI Provider |

### 飲食日記

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/diary/` | 新增日記（自動觸發 Celery AI 分析） |
| GET | `/api/v1/diary/` | 我的日記列表（含 components + ai_analysis） |
| GET | `/api/v1/diary/{id}/` | 取得單筆日記 |
| PATCH | `/api/v1/diary/{id}/` | 部分更新 |
| DELETE | `/api/v1/diary/{id}/` | 刪除 |

### 食物資料庫

| Method | Endpoint | 說明 |
|---|---|---|
| GET | `/api/v1/foods/?search=雞胸` | 列表 + 名稱 / 類別搜尋 |
| POST | `/api/v1/foods/` | 新增 |
| GET/PUT/PATCH/DELETE | `/api/v1/foods/{id}/` | CRUD |

### AI 分析

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/ai/analyze/{diary_id}/` | 重新觸發 AI 分析（202 非同步 / 200 cache hit） |
| GET | `/api/v1/ai/my-analyses/` | 我的所有 AI 分析紀錄 |

### 系統

| Method | Endpoint | 說明 |
|---|---|---|
| GET | `/health/` | 健康檢查（DB + Redis 連線狀態） |

---

## 測試策略

採用 **分層測試金字塔**：

```
       ┌──────────────┐
       │  test_views  │  ← API 整合測試（少量，覆蓋關鍵流程）
       ├──────────────┤
       │  test_tasks  │  ← Celery task 控制流程
       ├──────────────┤
       │ test_services│  ← 業務邏輯（最大量、最快、最穩定）
       ├──────────────┤
       │  test_models │  ← Model property / 計算邏輯
       └──────────────┘
```

### 測試重點

- **業務邏輯隔離**：所有 AI 呼叫 mock 掉，測試只驗證流程控制與資料正確性
- **factory_boy Traits**：用 `DiaryEntryFactory(completed=True)` 一行建立完整測試資料
- **freezegun 凍結時間**：測試 BMI / 年齡 / 每日營養計算等時間相關邏輯
- **冪等性測試**：重複觸發同一 task 不應產生重複資料
- **權限隔離測試**：跨使用者資料不可存取（401 / 404）
- **Transaction rollback 測試**：聚合失敗時，components 不應殘留

### 執行

```bash
# 完整測試 + 覆蓋率
pytest

# 只跑某個 app
pytest diary/tests/

# 顯示未覆蓋行數
pytest --cov-report=term-missing
```

`pytest.ini` 已設定 `--reuse-db` 加速本地反覆執行。

---

## CI/CD Pipeline

### CI（`.github/workflows/ci.yml`）

觸發：所有 branch push、PR 到 `develop` / `main`

```
[Checkout] → [Setup Python 3.12] → [Cache pip] → [Install]
   → [Run pytest --cov-fail-under=70]
   → [Django system check]
   → [Docker build 驗證（不 push）]
```

### CD（`.github/workflows/cd.yml`）

觸發：push 到 `main`

```
[Checkout] → [Login Docker Hub] → [Setup Buildx]
   → [Build image with tags: <commit_sha> + latest]
   → [Push to Docker Hub]
```

Image tag 策略：`{commit_sha}` 用於版本追蹤，`latest` 用於開發環境拉取。

---

## 未來規劃

### 短期（已規劃）

- [ ] **OpenTelemetry tracing**：追蹤 Request → Service → AI API 全鏈路延遲
- [ ] **Prometheus metrics**：暴露 cache hit rate、AI 呼叫成本、task 成功率
- [ ] **Rate limiting**：基於 Redis 的 per-user 限流（防 AI 成本爆炸）
- [ ] **每日 / 每週飲食趨勢分析**（aggregation + chart API）

### 中期

- [ ] **資料庫索引優化**：針對 `(user, date)`、`(food_name)` 加複合索引
- [ ] **Read replica**：讀寫分離（列表查詢走 replica）
- [ ] **AI Provider fallback chain**：OpenAI 失敗自動切換到 Gemini
- [ ] **React / Vue 前端**：前後端完全分離

---
