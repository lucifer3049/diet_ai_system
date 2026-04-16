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

---

## 技術棧

### 後端
- Python 3.12
- Django
- Django REST Framework
- PostgreSQL

### AI
- OpenAI API
- Google Gemini API

### DevOps
- Docker
- Docker Compose
- GitHub Actions（CI/CD）

---

## 專案結構（規劃中）




## API 規劃
```
# 使用者（users）
POST   /api/auth/register/          ← 註冊
POST   /api/auth/login/             ← 登入（取得 JWT token）
POST   /api/auth/token/refresh/     ← 刷新 token
GET    /api/users/me/               ← 取得自己的資料
PATCH  /api/users/me/               ← 更新自己的資料

# 食物資料庫（nutrition）
GET    /api/foods/                  ← 列出所有食物
POST   /api/foods/                  ← 新增食物
GET    /api/foods/{id}/             ← 取得單一食物

# 飲食日記（diary）
GET    /api/diary/                  ← 列出我的日記
POST   /api/diary/                  ← 新增一筆日記
GET    /api/diary/{id}/             ← 取得單一日記
PATCH  /api/diary/{id}/             ← 更新日記
DELETE /api/diary/{id}/             ← 刪除日記
POST   /api/diary/{id}/add-food/    ← 新增食物到日記
```