# 指令參考

## Django 指令

### Migration

```bash
# 偵測 model 變更，產生 migration 檔
python manage.py makemigrations

# 套用所有 migration 到資料庫
python manage.py migrate

# 查看每個 app 的 migration 套用狀態
python manage.py showmigrations

# 只套用特定 app
python manage.py migrate diary

# 回退到某個 migration（危險，會刪資料）
python manage.py migrate diary 0005
```

### 開發伺服器

```bash
# 啟動開發伺服器
python manage.py runserver --settings=config.settings.development

# 指定 port
python manage.py runserver 0.0.0.0:8000 --settings=config.settings.development
```

### Shell

```bash
# 進入 Django shell（可直接操作 ORM）
python manage.py shell

# 進入 shell_plus（需安裝 django-extensions，自動 import 所有 model）
python manage.py shell_plus
```

### 管理員

```bash
# 建立 superuser
python manage.py createsuperuser
```

### 靜態檔案

```bash
# 收集靜態檔案到 STATIC_ROOT（production 用）
python manage.py collectstatic
```

### 系統檢查

```bash
# 檢查設定與 model 是否有問題
python manage.py check
```

### 本專案自訂指令

```bash
# 從本地 CSV 匯入衛福部 FDA 食品成分資料
python manage.py import_taiwan_fda --file /path/to/fda_data.csv

# 從 URL 匯入
python manage.py import_taiwan_fda --url https://example.com/fda.csv

# 指定 CSV 編碼（衛福部 CSV 有時為 big5）
python manage.py import_taiwan_fda --file fda.csv --encoding big5
```

---

## Celery 指令

```bash
# 啟動 worker（本機開發用）
celery -A config worker --loglevel=info

# 啟動 worker，限制 concurrency
celery -A config worker --loglevel=info --concurrency=2

# 啟動 Celery Beat（定時任務，例如 FDA 每日同步）
celery -A config beat --loglevel=info

# 查看已註冊的 task
celery -A config inspect registered

# 手動觸發 task（在 Django shell 內）
from nutrition.tasks import sync_taiwan_fda_task
sync_taiwan_fda_task.delay()
```

---

## pytest 指令

```bash
# 執行所有測試 + 覆蓋率報告
pytest

# 只跑某個 app
pytest diary/tests/

# 顯示每個 test 名稱
pytest -v

# 顯示未覆蓋行號
pytest --cov-report=term-missing

# 只跑某個 test function
pytest diary/tests/test_services.py::TestDiaryService::test_cache_hit

# 跳過標記為 slow 的測試
pytest -m "not slow"
```

---

## Docker 指令

### 基本操作

```bash
# 啟動所有服務（含 rebuild）
docker compose up --build

# 背景執行
docker compose up -d --build

# 關閉所有服務
docker compose down

# 關閉並刪除 volume（資料庫資料會消失，慎用）
docker compose down -v

# 重新建立特定服務
docker compose up --build web
```

### 查看狀態與日誌

```bash
# 查看所有服務狀態
docker compose ps

# 查看某服務的即時日誌
docker compose logs -f web
docker compose logs -f celery
docker compose logs -f celery-beat

# 查看最後 100 行
docker compose logs --tail=100 celery
```

### 在容器內執行指令

```bash
# 執行 migration
docker compose exec web python manage.py migrate

# 產生 migration
docker compose exec web python manage.py makemigrations

# 建立 superuser
docker compose exec web python manage.py createsuperuser

# 進入 Django shell
docker compose exec web python manage.py shell

# 執行測試
docker compose exec web pytest

# 進入容器的 bash
docker compose exec web bash
docker compose exec db bash

# 進入 PostgreSQL CLI
docker compose exec db psql -U ${DB_USER} -d ${DB_NAME}
```

### Image 管理

```bash
# 查看 build 的 image
docker images

# 刪除未使用的 image / container / volume（清理空間）
docker system prune -f

# 強制重新 build（不用 cache）
docker compose build --no-cache
```

### 本專案服務對應

| 服務名稱 | 說明 | Port |
|---|---|---|
| `web` | Django 應用程式 | 8000 |
| `db` | PostgreSQL 15 + pgvector | 5433（本機）→ 5432（容器） |
| `redis` | Redis 7 | 6379 |
| `celery` | Celery Worker | — |
| `celery-beat` | Celery Beat（定時任務） | — |
