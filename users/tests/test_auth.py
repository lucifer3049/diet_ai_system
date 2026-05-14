import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'

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
        assert User.objects.filter(username='newuser').exists()