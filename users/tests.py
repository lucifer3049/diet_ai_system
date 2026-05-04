from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model


User = get_user_model()

class AuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'

    
    def test_register_success(self):
        """測試正常註冊"""
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'testuser')

    def test_register_password_mismatch(self):
        """測試密碼不一致"""
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Wrong1234!'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """測試帳號重複"""
        User.objects.create_user(username='testuser', password='Test1234!')
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'Test1234!',
            'password_confirm': 'Test1234!'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        """測試正常登入"""
        User.objects.create_user(username='testuser', password='Test1234!')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'Test1234!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """測試錯誤密碼"""
        User.objects.create_user(username='testuser', password='Test1234!')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'WrongPassword!'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='Test1234!'
        )
        # 登入取得 token
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'Test1234!'
        })
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_profile(self):
        """測試取得個人資料"""
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_update_profile(self):
        """測試更新個人資料"""
        response = self.client.patch('/api/v1/users/me/', {
            'height': 175,
            'weight': 70,
            'gender': 'male'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['height']), 175)

    def test_profile_without_auth(self):
        """測試未登入無法存取"""
        self.client.credentials()  # 清除 token
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        