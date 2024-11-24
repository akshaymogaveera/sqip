import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework import status

VALIDATE_TOKEN_URL = '/api/validate/token/'
AUTHENTICATE_USER_URL = '/api/auth/'

@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='testpassword')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def mock_get_token():
    with patch("main.utils.getToken") as mock_token:
        mock_token.return_value = ("mock_refresh_token", "mock_access_token")
        yield mock_token

@pytest.mark.django_db
class TestValidateToken:
    def test_validate_token_authenticated(self, api_client, user, mock_get_token):
        api_client.force_authenticate(user=user)
        response = api_client.get(VALIDATE_TOKEN_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Success'

    def test_validate_token_unauthenticated(self, api_client):
        response = api_client.get(VALIDATE_TOKEN_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data == {'detail': 'Authentication credentials were not provided.'}

    def test_validate_token_invalid_method(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(VALIDATE_TOKEN_URL)  # Invalid method
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_validate_token_malformed_token(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer malformed_token")
        response = api_client.get(VALIDATE_TOKEN_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'detail' in response.data


@pytest.mark.django_db
class TestAuthenticateUser:
    def test_authenticate_user_success(self, api_client, user, mock_get_token):
        response = api_client.post(AUTHENTICATE_USER_URL, {'username': 'testuser'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Success'

    def test_authenticate_user_missing_username(self, api_client):
        response = api_client.post(AUTHENTICATE_USER_URL, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'status': 'Failed', 'message': 'Username is required'}

    def test_authenticate_user_not_found(self, api_client):
        response = api_client.post(AUTHENTICATE_USER_URL, {'username': 'nonexistentuser'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {'status': 'Failed', 'message': "User not found"}

    def test_authenticate_user_case_insensitive(self, api_client, user, mock_get_token):
        response = api_client.post(AUTHENTICATE_USER_URL, {'username': 'TESTUSER'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {'status': 'Failed', 'message': "User not found"}

    def test_authenticate_user_with_whitespace(self, api_client, user, mock_get_token):
        response = api_client.post(AUTHENTICATE_USER_URL, {'username': ' testuser '})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {'status': 'Failed', 'message': "User not found"}

    def test_authenticate_user_invalid_method(self, api_client):
        response = api_client.get(AUTHENTICATE_USER_URL)  # Invalid method
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_authenticate_user_empty_body(self, api_client):
        response = api_client.post(AUTHENTICATE_USER_URL, None)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

