# 2026_04_15 將資料庫轉移到postgresql

1. 安裝 pip install psycopg2-binary==2.9.9
2. 設定 settings.py 
3. 需將機敏資料轉移至.env，安裝 pip install python-decouple==3.8，讀取參數config
4. 設定 DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql', # 連結的資料庫的參數
        'NAME': config('DB_NAME'), # DB的名稱
        'USER': config('DB_USER'), # DB登入帳號
        'PASSWORD': config('DB_PASSWORD'), # DB登入密碼
        'HOST': config('DB_HOST'), # DB的IP
        'PORT': config('DB_PORT'), # DB的埠
    }
}


# 2026_04_15 API筆記
```
Request → View → Serializer → Model → DB
                     ↓
                Response（JSON）
```

Request(請求) 使用者再透過瀏覽器、手機或Postman發送HTTP請求，例如 GET, POST, PUT , DELETE

View(視圖) 負責控制邏輯。接收到Request(請求)後決定要做甚麼事情

Serializer 負責Model <-> JSON的翻譯官，把Python的物件轉成JSON 或把JSON驗證後轉回物件
- 反序列化(Deserialization): 當發送POST請求時，會把JSON轉成Python能理解的物件，並檢查欄位格式是否正確
- 序列化(Serialization): 當回傳資料時，他把複雜的Python模型物件轉成JSON格式

Model(模型) 定義資料的樣子
- 告訴Django 資料庫裡應該長甚麼樣子，不會直接存資料，他是資料的結構

DB(資料庫)
- Django會透過 ORM 與DB溝通，所以不用寫SQL指令

View/ViewSet 處理請求邏輯，收到請求後決定做甚麼事情

Router 產生URL，不用手寫URL pattern

Response(回應) View會把Serializer處理的JSON資料包裝成Response回傳給使用者，通常是JSON格式


# Django的URL路由配置
```
urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
]
```
- path :Django內建用來定義網址的工具
- TokenObtainPairView&TokenRefreshView: 這是JWT(JSON Web Token) 驗證套件
● ObtainPair:用來換取令牌，登入
● Refresh: 用來刷新令牌，登入超過一段時間，會更新登入令牌

- urlpatterns: 路由清單
● RegisterView : 註冊，建立新帳號
● TokenObtainPairView: 登入，輸入帳密，成功後會給 Access Token
● TokenRefreshView: 延長登入，當Access Token過期時，會用Refresh Token
● UserProfileView: 查看自己的帳號資訊

- .as_view(): 此函數會把類別轉換成Django看得懂函數

# 2026_04_19 AI功能筆記

mkdir ai_analysis\services # 建立services 次檔案是為了多模型邏輯所統一管理的資料夾
type nul > ai_analysis\services\__init__.py
type nul > ai_analysis\services\base.py # base.py是存放多個模型的依賴
type nul > ai_analysis\services\openai_service.py