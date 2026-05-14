"""
測試使用者相關 API:
  - 註冊：成功、密碼不一致、帳號重複、弱密碼
  - 登入：成功、錯誤密碼、不存在帳號
  - 個人資料：讀取、更新、未認證拒絕
  - BMI/daily_nutrition_needs 計算結果
"""
import pytest
from rest_framework.test import APIClient
from users.tests.factories import UserFactory

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
PROFILE_URL = '/api/v1/users/me/'


@pytest.mark.django_db
class TestRegisterView:

    def test_register_success(self, api_client):
        response = api_client.post(REGISTER_URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!',
        })
        assert response.status_code == 201
        assert response.data['username'] == 'newuser'

    def test_register_does_not_return_password(self, api_client):
        """密碼不應出現在回應中"""
        api_client.post(REGISTER_URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!',
        })
        # 驗證 password 欄位不在 response
        response = api_client.post(REGISTER_URL, {
            'username': 'anotheruser',
            'email': 'another@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!',
        })
        assert 'password' not in response.data

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(REGISTER_URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Wrong1234!',
        })
        assert response.status_code == 400

    def test_register_duplicate_username(self, api_client, user):
        response = api_client.post(REGISTER_URL, {
            'username': user.username,
            'email': 'other@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!',
        })
        assert response.status_code == 400

    def test_register_weak_password_rejected(self, api_client):
        """Django 密碼強度驗證應拒絕太弱的密碼"""
        response = api_client.post(REGISTER_URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': '123',
            'password_confirm': '123',
        })
        assert response.status_code == 400

    def test_register_no_auth_required(self, api_client):
        """註冊不需要 JWT"""
        response = api_client.post(REGISTER_URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!',
        })
        assert response.status_code != 401


@pytest.mark.django_db
class TestLoginView:

    def test_login_success_returns_tokens(self, api_client, user):
        response = api_client.post(LOGIN_URL, {
            'username': user.username,
            'password': 'Test1234!',
        })
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, user):
        response = api_client.post(LOGIN_URL, {
            'username': user.username,
            'password': 'WrongPassword!',
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(LOGIN_URL, {
            'username': 'nobody',
            'password': 'Test1234!',
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserProfileView:

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client, user):
        self.client = authenticated_client
        self.user = user

    def test_get_profile_returns_200(self):
        response = self.client.get(PROFILE_URL)
        assert response.status_code == 200
        assert response.data['username'] == self.user.username

    def test_get_profile_includes_bmi(self):
        """有身高體重時應回傳計算好的 BMI"""
        response = self.client.get(PROFILE_URL)
        assert 'bmi' in response.data
        assert response.data['bmi'] is not None

    def test_get_profile_bmi_is_none_without_height(self):
        self.user.height = None
        self.user.save()
        response = self.client.get(PROFILE_URL)
        assert response.data['bmi'] is None

    def test_update_height_and_weight(self):
        response = self.client.patch(PROFILE_URL, {
            'height': 180,
            'weight': 75,
        })
        assert response.status_code == 200
        self.user.refresh_from_db()
        assert float(self.user.height) == 180

    def test_update_ai_provider_preference(self):
        
        response = self.client.patch(PROFILE_URL, {
            'preferred_ai_provider': 'gemini',
        })
        assert response.status_code == 200
        self.user.refresh_from_db()
        assert self.user.preferred_ai_provider == 'gemini'

    def test_cannot_update_username(self):
        """username 是 read_only，不應被修改"""
        original_username = self.user.username
        self.client.patch(PROFILE_URL, {'username': 'hacked'})
        self.user.refresh_from_db()
        assert self.user.username == original_username

    def test_unauthenticated_returns_401(self):
        response = APIClient().get(PROFILE_URL)
        assert response.status_code == 401
