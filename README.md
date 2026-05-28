# Diet AI System

> 結合 LLM 的個人化飲食追蹤後端系統。透過 Django REST Framework 提供 API，整合 OpenAI / Gemini 雙模型進行食物圖片辨識與飲食建議生成；採用**四層快取（含 pgvector 語意搜尋）**降低 AI 呼叫成本，**Celery 非同步任務**避免阻塞請求，**Service Layer** 架構維持可測試性與可擴充性。支援每位使用者獨立設定 AI Provider 與 API Key，並整合衛福部 FDA 食品營養資料庫。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)]()
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)]()
[![DRF](https://img.shields.io/badge/DRF-3.15-red)]()
[![Coverage](https://img.shields.io/badge/coverage-≥70%25-brightgreen)]()

---

## 目錄

- [專案動機與設計目標](#專案動機與設計目標)
- [系統架構](#系統架構)
- [資料模型](#資料模型)
- [核心設計決策](#核心設計決策)
- [技術棧](#技術棧)
- [專案結構](#專案結構)
- [快速開始](#快速開始)
- [API 概覽](#api-概覽)
- [測試策略](#測試策略)
- [CI/CD Pipeline](#cicd-pipeline)
- [未來規劃](#未來規劃)

---

---

## 專案動機與設計目標

直接每次呼叫 LLM 分析食物會造成：

- **成本爆炸**：相同食物（如「白米飯」）被反覆呼叫
- **延遲過高**：使用者新增日記時必須等待 3–5 秒
- **可靠性低**：第三方 API 限流或失敗會直接影響使用者體驗

本專案用 **多層快取 + 非同步處理 + 抽象化 Provider** 解決這些問題，同時維持可替換、可測試、可擴充的後端架構。

---

## 系統架構

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP + JWT
       ▼
┌──────────────────────────────────────────────────┐
│              Django REST Framework               │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Views   │→ │ Service  │→ │    Models     │  │
│  │ (Thin)   │  │  Layer   │  │    (ORM)      │  │
│  └──────────┘  └────┬─────┘  └───────┬───────┘  │
└───────────────────── ┼────────────── ┼───────────┘
                       │               │
        ┌──────────────┼───────────────┼────────────┐
        │              ▼               ▼            │
        │      ┌──────────────┐  ┌────────────┐    │
        │      │    Celery    │  │ PostgreSQL │    │
        │      │   Worker     │  │  (L2 Cache)│    │
        │      └──────┬───────┘  └────────────┘    │
        │             │                             │
        │             ▼                             │
        │      ┌──────────────┐  ┌────────────┐    │
        │      │    Redis     │  │  AI APIs   │    │
        │      │ (L1 Cache +  │  │  OpenAI /  │    │
        │      │   Broker)    │  │   Gemini   │    │
        │      └──────────────┘  └────────────┘    │
        └─────────────────────────────────────────┘
```

### 四層快取架構（文字分析的營養查詢）

```
食物名稱 ──▶ L1: Redis (~ms)
              │ miss
              ▼
           L2: PostgreSQL / FoodNutritionCache (~10ms)
              │ hit → 回填 L1；hit_count +1
              │ miss
              ▼
           L2.5: pgvector 語意搜尋 (~20ms)
              │ 精確名稱找不到時，找 cosine similarity ≥ 0.92 的近似快取
              │ 例：「豬排飯」→ 命中「排骨飯」
              │ hit → 回填 L1
              │ miss
              ▼
           L3: AI API (OpenAI / Gemini) (~3-5s)
              └─▶ 寫入 L2 + 非同步儲存 embedding + 回填 L1
```

實作位置：[diary/services.py](diary/services.py) → `DiaryService.get_nutrition_from_cache_or_ai()`
L2.5 實作：[nutrition/vector_service.py](nutrition/vector_service.py) → `FoodVectorService`

### 請求生命週期（新增飲食日記）

```
POST /api/v1/diary/
    │
    ▼
[View] 驗證 + 建立 DiaryEntry
    │                status = PENDING
    ├─有圖片──▶ analyze_diary_image_task.delay() ──┐
    │                                               │
    └─無圖片──▶ analyze_diary_entry_task.delay() ──┤
    │                                               │
    ▼                                               ▼
回傳 201（不阻塞）                       [Celery Worker]
                                         status → PROCESSING
                                         ├─ 圖片: AI Vision → bulk_create DiaryComponent
                                         │   → aggregate 加總 → 寫回 DiaryEntry
                                         └─ 文字: L1/L2/L3 取營養 → 寫回 DiaryEntry
                                                  → AI 飲食建議 → 寫入 AIAnalysis
                                         status → COMPLETED / FAILED
```

---

## 資料模型

### DiaryEntry（飲食日記）

使用者每一筆飲食紀錄的核心實體。建立時由 Celery task 非同步填入 AI 分析結果。

| 欄位 | 說明 |
|---|---|
| `user` | FK → User |
| `date`, `meal_type` | 日期與餐別（早/午/晚/點心） |
| `food_name` | 使用者輸入的食物名稱 |
| `image` | 食物照片（上傳時走圖片辨識流程） |
| `calories` ~ `sodium` | AI 分析後填入的 8 項營養素 |
| `status` | 當前分析狀態（見下方狀態機） |

**DiaryEntry 狀態機（[diary/state_machine.py](diary/state_machine.py)）**

```
PENDING ──▶ PROCESSING ──▶ COMPLETED
   │              │
   └──────────────┴──▶ FAILED ──▶ PENDING（reanalyze）
```

| 狀態 | 含意 |
|---|---|
| `pending` | 剛建立，等待 Celery 處理 |
| `processing` | Celery task 正在執行 |
| `completed` | AI 分析完成，營養素已填入 |
| `failed` | 分析失敗（max retries 耗盡後設定） |

### DiaryComponent（圖片辨識食物成份）

圖片辨識時，AI 將照片拆解成多個食物成份，每個成份獨立存一筆。

```
DiaryEntry (1) ──▶ DiaryComponent (N)
              例：雞腿便當 → [白飯, 雞腿, 醃蘿蔔, 滷蛋]
```

| 欄位 | 說明 |
|---|---|
| `diary_entry` | FK → DiaryEntry |
| `food_name`, `portion_description` | 成份名稱與估算份量 |
| `calories` ~ `sodium` | 該成份的 8 項營養素 |
| `source` | 來源標記（`ai_vision` / `ai_text` / `cache`） |

### AIAnalysis（AI 飲食建議）

文字分析流程完成後，由 `DiaryService` 建立，記錄 AI 給予的飲食評分與建議。

| 欄位 | 說明 |
|---|---|
| `diary_entry` | OneToOne → DiaryEntry |
| `summary` | 這餐的整體評價 |
| `suggestions` | 下一餐建議（JSON list） |
| `exceeded_nutrients` | 攝取過多的營養素（JSON list） |
| `lacking_nutrients` | 攝取不足的營養素（JSON list） |
| `nutrition_score` | 營養評分 1–100 |
| `ai_model_used` | 使用的模型（如 `openai:gpt-4o-mini`） |

### FoodNutritionCache（營養快取）

四層快取的 L2 層。AI 首次分析後存入，之後相同食物直接從此取值並 `hit_count +1`。

| 欄位 | 說明 |
|---|---|
| `food_name` | 正規化食物名稱（小寫、去空白） |
| `calories` ~ `sodium` | 8 項營養素 |
| `hit_count` | 命中次數（可分析哪些食物最熱門） |
| `data_source` | 資料來源：`ai`（AI分析）/ `taiwan_fda`（衛福部FDA）/ `manual`（手動） |
| `embedding` | pgvector 向量欄位（1536 維，`text-embedding-3-small` 生成） |

### User（使用者）

繼承 Django AbstractUser，新增：
- `height`、`weight`、`birth_date`、`gender`、`goal`、`preferred_ai_provider`
- **每位使用者獨立 API Key**：`openai_api_key`、`gemini_api_key`（Fernet 對稱加密儲存）
- **每位使用者獨立模型選擇**：`preferred_openai_model`、`preferred_gemini_model`
- Computed properties：`bmi`、`age`、`daily_nutrition_needs`（Harris-Benedict 公式）
- `to_ai_profile()`：組裝傳給 AI 的使用者基本資料 dict
- `get_api_key(provider)`：優先取使用者自訂 key，無則 fallback 至伺服器 `.env`
- `get_preferred_model(provider)`：取使用者偏好模型

---

## 核心設計決策

### 1. Service Layer 分層架構

**問題**：Django 預設容易陷入 Fat View / Fat Model，業務邏輯散落難以測試。

| 層級 | 職責 | 不該做的事 |
|---|---|---|
| **View** | HTTP 解析、權限驗證、回傳 Response | 業務邏輯、複雜查詢 |
| **Service** | 業務流程、Cache 策略、Transaction 控制 | 直接回傳 DRF Response |
| **Task** | Celery 進入點、retry 策略 | 業務邏輯（委派給 service） |
| **Serializer** | 驗證與序列化 | 跨模組協調 |
| **Model** | 資料結構與簡單 property（如 BMI） | I/O、外部呼叫 |

Service 可以脫離 HTTP 層獨立測試，View 多數 < 30 行。

### 2. AI Provider 抽象化（Strategy + Factory）

**問題**：OpenAI 與 Gemini SDK 介面完全不同；直接寫在業務邏輯裡，新增 Provider 需改多處。

```python
# ai_analysis/services/base.py  ← 定義合約
class BaseAIService(ABC):
    @abstractmethod
    def analyze_food_nutrition(...) -> NutritionAnalysisResult: ...
    @abstractmethod
    def give_dietary_advice(...) -> DietaryAdviceResult: ...
    @abstractmethod
    def _do_call_vision_api(...) -> str: ...

    # 共用：Prompt 組裝、JSON 解析、Vision 流程
    def analyze_food_image(...) -> ImageAnalysisResult: ...

# ai_analysis/services/__init__.py  ← Factory
def get_ai_service(provider: str) -> BaseAIService:
    return {'openai': OpenAIService, 'gemini': GeminiService}[provider]()
```

- 各 Provider 只需實作 `_call_api` 和 `_do_call_vision_api`
- 回傳值用 `@dataclass` 強型別化（`NutritionAnalysisResult` / `DietaryAdviceResult` / `ImageAnalysisResult`）
- **新增 Provider 的成本**：一支新的 service 檔 + 一行 factory 註冊

### 3. DiaryNutritionDTO（型別化資料傳遞）

`diary/dto.py` 的 `DiaryNutritionDTO` 是一個 frozen dataclass，統一從 `DiaryEntry` 組裝傳給 AI 的資料格式。

```python
# 用法：diary/services.py 和 ai_analysis/analysis_service.py 共用同一個 from_entry()
DiaryNutritionDTO.from_entry(diary_entry).to_dict()
```

避免兩個 service 各自維護相同的 dict 組裝邏輯（DRY）。

### 4. AI Provider 三層優先順序

```
Request body（前端臨時指定）
       ↓ 若無
User.preferred_ai_provider（使用者偏好）
       ↓ 若無
config('AI_PROVIDER')（環境變數預設）
```

實作於 `ai_analysis/views.py::AnalyzeDiaryView`。前端可在不修改帳號設定的前提下，臨時切換 Provider 做 A/B 比較。

### 10. 每位使用者獨立 AI Key（Fernet 加密）

**問題**：伺服器統一的 API Key 無法控制個別使用者成本，且多人共用同一配額限制。

```python
# users/fields.py — EncryptedCharField
class EncryptedCharField(models.TextField):
    def from_db_value(self, ...): return fernet.decrypt(value)   # 讀取時解密
    def get_prep_value(self, ...): return fernet.encrypt(value)   # 寫入時加密
```

Key 優先順序（`users/models.py::get_api_key()`）：

```
使用者自訂 API Key（資料庫加密儲存）
       ↓ 若未設定
伺服器 .env 的 OPENAI_API_KEY / GEMINI_API_KEY
```

API 金鑰在 serializer 輸出時自動遮罩（只顯示末 6 碼）。  
設定端點：`PATCH /api/v1/users/me/settings/`

### 11. 衛福部 FDA 食品資料庫整合

**問題**：AI 每次分析「白米飯」都要呼叫 API，浪費成本；官方資料庫可直接提供精確數據。

- **資料來源**：臺灣衛生福利部食品藥物管理署（TFND）食品成分資料庫 CSV
- **匯入方式**：`update_or_create`，確保重複匯入冪等
- **自動同步**：Celery Beat 每天凌晨 3:00 自動執行（可透過 `TAIWAN_FDA_SYNC_ENABLED` 開關）
- **手動匯入**：`python manage.py import_taiwan_fda --url <URL>` 或 `--file <path>`

```python
# 任意觸發一次手動同步（Admin 或 CLI）
from nutrition.tasks import sync_taiwan_fda_task
sync_taiwan_fda_task.delay()
```

### 12. pgvector 語意快取（L2.5）

**問題**：「豬排飯」沒有精確快取，但「排骨飯」有，應該能複用。

- 向量由伺服器統一的 `OPENAI_API_KEY` 生成（`text-embedding-3-small`，1536 維）
- 相似度閾值：cosine similarity ≥ 0.92（即 cosine distance < 0.08）
- AI 分析後非同步儲存 embedding（不阻塞主流程，失敗靜默略過）
- 若 `OPENAI_API_KEY` 未設定，L2.5 自動跳過，不影響整體流程

### 5. Celery 非同步任務拆分

`analyze_diary_entry_task` 與 `analyze_diary_image_task` 是兩支獨立 task，原因：

- **不同 retry 策略**：圖片辨識失敗成本更高，可獨立調整 `max_retries`
- **獨立 concurrency 控制**：Vision API 通常較慢且配額較少，需限流
- **獨立監控**：成功率與平均延遲可分開觀測

**Retry 設計**：失敗時 status 維持在 `PROCESSING`（讓下一次 retry 能繼續執行）；只有 `retries >= max_retries` 時才設為 `FAILED`。

```python
except Exception as exc:
    if self.request.retries >= self.max_retries:
        DiaryEntry.objects.filter(id=diary_entry_id).update(status=DiaryEntry.StatusChoices.FAILED)
    raise self.retry(exc=exc)
```

### 6. 圖片辨識的資料一致性

```python
# diary/services.py
with transaction.atomic():
    cls._save_components(...)     # bulk_create N 筆 DiaryComponent（1 次 INSERT）
    cls._aggregate_to_diary(...)  # 加總後 update_fields 寫回 DiaryEntry
```

`transaction.atomic` 保證「components 全部建立 + DiaryEntry 更新」要嘛全成功，要嘛全 rollback，不會有拆解了但沒加總的中間狀態。

### 7. 環境分離

| 環境 | 重點差異 |
|---|---|
| `base.py` | 共用 INSTALLED_APPS、DRF、JWT、Celery、Spectacular |
| `development.py` | DEBUG=True、verbose logging、寬鬆 CORS |
| `production.py` | DEBUG=False、JSON structured log、安全 header |
| `testing.py` | SQLite in-memory、`CELERY_TASK_ALWAYS_EAGER=True`、MD5 hasher 加速 |

### 8. 統一錯誤格式

DRF 預設錯誤格式不一致（有時 `{"detail": ...}` 有時 `{"field": [...]}`）。透過 `config/exceptions.py` 統一包裝：

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": { ... }
  }
}
```

### 9. 觀測性

- **健康檢查端點** `config/health.py`：同時測試 DB + Redis 連線，可作為 K8s readiness probe
- **結構化日誌**：production 輸出 JSON 格式，方便 ELK / Loki 收集
- **AI 呼叫全程記錄**：每次 Provider 呼叫前後都有 `logger.info`，便於排查成本與延遲

---

## 技術棧

### Backend
- **Python 3.12** / **Django 5.0** / **Django REST Framework 3.15**
- **PostgreSQL 15 + pgvector** — 主資料庫 + 向量搜尋（`pgvector/pgvector:pg15` image）
- **Redis 7** — L1 快取 + Celery broker/backend
- **Celery 5.4** + **Celery Beat** — 非同步任務佇列 + 定時任務（FDA 每日同步）
- **drf-spectacular** — OpenAPI 3.0 自動產生（Swagger UI + ReDoc）
- **SimpleJWT** — JWT 認證 + token rotation + blacklist
- **cryptography (Fernet)** — API Key 欄位對稱加密

### AI Integration
- **OpenAI API**：`gpt-4o-mini`（文字）、`gpt-4o`（Vision）
- **Google Gemini API**：`gemini-2.5-flash`（文字 + Vision）

### Testing
- **pytest** + **pytest-django** + **pytest-cov**（覆蓋率門檻 70%）
- **factory_boy** + **Faker** — 測試資料工廠
- **freezegun** — 時間相關邏輯測試（BMI、年齡計算）

### DevOps
- **Docker** + **Docker Compose** — 多服務編排（web / db / redis / celery）
- **GitHub Actions** — CI（測試 + Docker build）/ CD（push image to Docker Hub）
- **Gunicorn** + **Nginx**（production compose）

---

## 專案結構

```
diet-ai-system/
├── config/
│   ├── settings/
│   │   ├── base.py              # 共用設定（DRF、JWT、Celery、Cache）
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py           # SQLite + CELERY_ALWAYS_EAGER
│   ├── celery.py                # Celery app 初始化
│   ├── exceptions.py            # 統一錯誤回應格式
│   ├── health.py                # 健康檢查（DB + Redis）
│   └── urls.py
│
├── users/
│   ├── models.py                # User + BMI + Harris-Benedict + to_ai_profile() + get_api_key()
│   ├── fields.py                # EncryptedCharField（Fernet 透明加解密）
│   ├── serializers.py           # UserSerializer / UserAISettingsSerializer
│   ├── views.py                 # Register / Profile / UserAISettingsView
│   └── urls.py
│
├── nutrition/
│   ├── models.py                # Food（食物資料庫）/ FoodNutritionCache（L2 快取 + embedding）
│   ├── cache.py                 # Redis L1 cache helpers
│   ├── vector_service.py        # L2.5 pgvector 語意搜尋（FoodVectorService）
│   ├── fda_importer.py          # TaiwanFDAImporter（CSV/URL 匯入）
│   ├── tasks.py                 # sync_taiwan_fda_task（Celery Beat 每日 3:00）
│   ├── management/commands/
│   │   └── import_taiwan_fda.py # 手動匯入 CLI（--file / --url）
│   ├── views.py
│   └── urls.py
│
├── diary/                       # 飲食日記（核心 domain）
│   ├── models.py                # DiaryEntry / DiaryComponent
│   ├── dto.py                   # DiaryNutritionDTO — 傳給 AI 的標準資料結構
│   ├── state_machine.py         # LEGAL_TRANSITIONS / is_legal_transition()
│   ├── services.py              # 三層快取 + 圖片辨識 + AI 流程編排
│   ├── tasks.py                 # Celery tasks（文字 / 圖片，各自獨立 retry）
│   ├── serializers.py           # DiaryEntrySerializer / DiaryComponentSerializer
│   ├── views.py                 # DiaryEntryViewSet（CRUD）
│   ├── urls.py
│   └── migrations/
│
├── ai_analysis/
│   ├── services/
│   │   ├── base.py              # BaseAIService（ABC）+ Dataclasses + Prompt 組裝
│   │   ├── openai_service.py    # OpenAI 實作
│   │   ├── gemini_service.py    # Gemini 實作
│   │   └── __init__.py          # Factory: get_ai_service(provider)
│   ├── models.py                # AIAnalysis（飲食建議結果）
│   ├── analysis_service.py      # AIAnalysisService（reanalyze 業務邏輯）
│   ├── serializers.py
│   ├── tasks.py                 # reanalyze_diary_task
│   ├── views.py                 # AnalyzeDiaryView / MyAnalysisListView
│   ├── urls.py
│   └── migrations/
│
├── .github/workflows/
│   ├── ci.yml                   # test + docker build 驗證
│   └── cd.yml                   # push image to Docker Hub
│
├── conftest.py                  # pytest fixtures（user / diary / cache）
├── docker-compose.yml
├── docker-compose.prod.yml      # 含 Nginx + Gunicorn
├── Dockerfile
├── pytest.ini
└── requirements.txt
```
---

## 快速開始

### 環境需求
- Docker 20.10+
- Docker Compose v2

### Docker 啟動

```bash
# 1. 複製環境變數範本
cp .env.example .env
# 填入：SECRET_KEY、DB_*、REDIS_URL、OPENAI_API_KEY 或 GEMINI_API_KEY

# 2. 啟動所有服務（web / db / redis / celery）
docker compose up --build

# 3. 建立管理員帳號
docker compose exec web python manage.py createsuperuser
```

開啟 http://localhost:8000/api/docs/ 查看 Swagger UI。

### 常用指令

```bash
# 進入容器
docker exec -it diet-ai-web bash

# 執行 migration
docker compose exec web python manage.py migrate

# 執行測試（含覆蓋率）
docker compose exec web pytest

# 查看 Celery worker 日誌
docker compose logs -f celery

# 停止並清空資料（含 volume）
docker compose down -v
```

### 本機開發（不使用 Docker）

```bash
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

pip install -r requirements.txt
python manage.py migrate --settings=config.settings.development
python manage.py runserver --settings=config.settings.development

# 另開終端啟動 Celery worker
celery -A config worker --loglevel=info

# 進入Django shell，可以測試ORM
python manage.py shell

# 離開venv
deactivate
```

### 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `SECRET_KEY` | ✓ | Django secret key |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | ✓ | PostgreSQL 連線設定 |
| `REDIS_URL` | ✓ | Redis 連線（Celery + Cache 共用） |
| `OPENAI_API_KEY` | 擇一 | 伺服器預設 OpenAI API key（食物名稱 embedding 也用此 key） |
| `GEMINI_API_KEY` | 擇一 | 伺服器預設 Google Gemini API key |
| `AI_PROVIDER` | — | 預設 AI provider（`openai` / `gemini`，預設 `openai`） |
| `OPENAI_MODEL` | — | 伺服器預設 OpenAI 模型，預設 `gpt-4o-mini` |
| `GEMINI_MODEL_NAME` | — | 伺服器預設 Gemini 模型，預設 `gemini-2.5-flash` |
| `FIELD_ENCRYPTION_KEY` | ✓ | Fernet 32-byte key（`Fernet.generate_key()`），加密使用者 API Key |
| `TAIWAN_FDA_SYNC_ENABLED` | — | `True` 開啟 Celery Beat 每日自動同步 FDA 資料（預設 `False`） |
| `TAIWAN_FDA_CSV_URL` | — | 衛福部 FDA 食品成分 CSV 下載網址（需設定才能自動同步） |

---

## API 概覽

完整 OpenAPI schema：`/api/schema/` ｜ Swagger UI：`/api/docs/` ｜ ReDoc：`/api/redoc/`

所有 `/api/v1/` 端點均需 JWT 認證：`Authorization: Bearer <access_token>`

### 認證

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/auth/register/` | 使用者註冊（回傳 username + email） |
| POST | `/api/v1/auth/login/` | 取得 JWT access + refresh token |
| POST | `/api/v1/auth/token/refresh/` | 用 refresh token 換新 access token |

### 使用者

| Method | Endpoint | 說明 |
|---|---|---|
| GET | `/api/v1/users/me/` | 取得個人資料（含 BMI、年齡、每日營養建議） |
| PATCH | `/api/v1/users/me/` | 更新身高、體重、目標、偏好 AI Provider |
| GET | `/api/v1/users/me/settings/` | 取得 AI 設定（API key 末 6 碼遮罩 + 偏好模型） |
| PATCH | `/api/v1/users/me/settings/` | 更新個人 API key、偏好模型 |

**PATCH `/api/v1/users/me/settings/` 範例**

```json
{
  "preferred_ai_provider": "openai",
  "openai_api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx",
  "preferred_openai_model": "gpt-4o",
  "gemini_api_key": null,
  "preferred_gemini_model": "gemini-2.5-flash"
}
```

### 飲食日記

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/diary/` | 新增日記（自動觸發非同步 AI 分析） |
| GET | `/api/v1/diary/` | 我的日記列表（含 components + ai_analysis） |
| GET | `/api/v1/diary/{id}/` | 取得單筆日記詳細 |
| PATCH | `/api/v1/diary/{id}/` | 部分更新 |
| DELETE | `/api/v1/diary/{id}/` | 刪除 |

**POST `/api/v1/diary/` 行為說明**

- 上傳 `image` → 觸發圖片辨識（`analyze_diary_image_task`）→ 自動建立 `DiaryComponent`
- 無圖片 → 文字分析（`analyze_diary_entry_task`）→ 三層快取查詢 + 飲食建議

**回應中 `status` 欄位**

```json
{
  "id": 1,
  "status": "processing",        // pending / processing / completed / failed
  "calories": null,              // 分析完成前為 null
  "components": [],              // 圖片辨識完成後有值
  "ai_analysis": { ... }        // 文字分析完成後有值
}
```

### 食物資料庫

| Method | Endpoint | 說明 |
|---|---|---|
| GET | `/api/v1/foods/` | 列表（支援 `?search=` 名稱搜尋） |
| POST | `/api/v1/foods/` | 新增食物 |
| GET/PATCH/DELETE | `/api/v1/foods/{id}/` | 單筆操作 |

**手動觸發 FDA 資料同步（需 admin 或 CLI）**

```bash
# CLI
python manage.py import_taiwan_fda --url https://example.com/fda.csv
python manage.py import_taiwan_fda --file /path/to/fda_data.csv --encoding big5

# Celery（非同步）
from nutrition.tasks import sync_taiwan_fda_task
sync_taiwan_fda_task.delay()
```

### AI 分析

| Method | Endpoint | 說明 |
|---|---|---|
| POST | `/api/v1/ai/analyze/{diary_id}/` | 觸發或取得 AI 飲食建議分析 |
| GET | `/api/v1/ai/my-analyses/` | 我的所有 AI 分析紀錄 |

**POST 行為**

- 已有分析結果 → 直接回傳 `200`（cache hit，不重複呼叫 AI）
- 尚未分析 → 排程非同步 task，回傳 `202`
- 支援 `{"provider": "gemini"}` 臨時指定 AI Provider

---

## 測試策略

採用**分層測試金字塔**，底層比頂層多：

```
       ┌──────────────────┐
       │   test_views     │  ← API 整合測試（覆蓋關鍵流程與權限邊界）
       ├──────────────────┤
       │   test_tasks     │  ← Celery 控制流程（retry、idempotent、FAILED 設定時機）
       ├──────────────────┤
       │  test_services   │  ← 業務邏輯（最大量、最快、最穩定）
       ├──────────────────┤
       │   test_models    │  ← Model property（BMI、Harris-Benedict）
       └──────────────────┘
```

### 測試重點

- **AI 呼叫隔離**：所有 AI 呼叫 mock，測試只驗證流程控制與資料正確性
- **factory_boy**：`DiaryEntryFactory(completed=True)` 一行建立完整測試資料
- **freezegun 凍結時間**：測試 BMI / 年齡 / 每日營養需求等時間相關邏輯
- **冪等性測試**：status 為 `completed` 的日記再次觸發 task，不應重複分析
- **Retry 邊界測試**：第 1 次失敗維持 `processing`，第 3 次（max_retries）才設為 `failed`
- **Transaction rollback**：`_aggregate_to_diary` 失敗時，components 不應殘留
- **權限隔離**：跨使用者資料存取應回傳 404（不洩漏存在性）

### 執行

```bash
# 完整測試 + 覆蓋率報告
pytest

# 只跑單一 app
pytest diary/tests/

# 顯示未覆蓋行數
pytest --cov-report=term-missing

# 只跑特定標記
pytest -m "not slow"
```

---

## CI/CD Pipeline

### CI（`.github/workflows/ci.yml`）

觸發：所有 branch push、PR 到 `develop` / `main`

```
Checkout → Setup Python 3.12 → Cache pip → Install deps
  → Run pytest --cov-fail-under=70
  → Django system check (manage.py check)
  → Docker build 驗證（不 push）
```

### CD（`.github/workflows/cd.yml`）

觸發：push 到 `main`

```
Checkout → Login Docker Hub → Setup Buildx
  → Build image（tags: <commit_sha> + latest）
  → Push to Docker Hub
```

Image tag 策略：`{commit_sha}` 用於版本追蹤，`latest` 供開發環境快速拉取。

---

## 未來規劃

### 短期

- [ ] **Rate limiting**：基於 Redis 的 per-user 限流（防 AI 成本爆炸）
- [ ] **每日 / 每週飲食趨勢**：aggregation API + 圖表資料
- [ ] **AI Provider fallback chain**：OpenAI 失敗自動切換到 Gemini
- [ ] **Prometheus metrics**：暴露 cache hit rate、AI 呼叫次數、task 成功率
- [ ] **pgvector 索引優化**：為 embedding 欄位建立 HNSW / IVFFlat 索引，提升大量資料時的搜尋效能
- [ ] **FDA 同步狀態 API**：查詢最後同步時間、匯入筆數、失敗原因

### 中期

- [ ] **OpenTelemetry tracing**：追蹤 Request → Service → AI API 全鏈路延遲
- [ ] **資料庫索引優化**：`(user, date)`、`food_name` 加複合索引
- [ ] **Read replica**：讀寫分離（列表查詢走 replica）
- [ ] **React / Vue 前端**：前後端完全分離，使用者可在 UI 設定個人 AI Key 與模型
