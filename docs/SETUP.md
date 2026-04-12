# 確認電腦環境
# 確認Python版本
python --version

# 確認pip
pip --version

# 確認 git
git --version


# 建立虛擬機
python -m venv venv

# 啟動虛擬機 windows
venv\Scripts\activate

# MAC / Linux
source venv/bin/activate


# 安裝套件
pip install django==5.0.6
pip install djangorestframework==3.15.2
pip install psycopg2-binary==2.9.9
pip install redis==5.0.4
pip install django-redis==5.4.0
pip install djangorestframework-simplejwt==5.3.1
pip install python-decouple==3.8
pip install openai==1.35.0
pip install google-generativeai==0.7.2
pip install Pillow==10.3.0
pip install django-cors-headers==4.3.1
pip install celery==5.4.0

# 產生依賴紀錄.txt
pip freeze > requirements.txt


# 建立django 專案
django-admin startproject config .

# 建立資料夾 
mkdir -p config/settings  # 分離開發/產生設定
mkdir -p docker # docker相關文件
mkdir -p docs 
mkdir -p tests  # 測試文件

touch .env # 建立.env Linus/Mac
New-Item .env # 建立.env windows


touch .env.example # 環境變數 會上傳到git Linus/Mac
New-Item .env.example # 建立環境變數 windows

touch .gitignore
New-Item .gitignore

# 建立Django的模組
python manage.py startapp users # 使用者 app
python manage.py startapp diary # 飲食日記 app
python manage.py startapp nutrition # 營養分析 app
python manage.py startapp ai_analysis # AI 分析 app

# 確認環境輸出結果
python manage.py check 


# 虛擬機Linux/Mac指令
ls -la  # 查看資料結構


# 虛擬機windows
ls -Force # 查看所有檔案(含隱藏)


# git 指令
git init # 初始化
git add . # 加入全部檔案
git remote add origin https://github.com/你的帳號/diet_ai_system.git #連接遠端
git branch -M main # 推上主分支
git push -u origin main # 推上遠端主分支