from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse


# Test User Registration Endpoint
class TestLoginUser(APITestCase):
    def setUp(self):

        self.login_data = {
            "email": "theresaobamwonyi@gmail.com",
            "password": "resa12345"
        }

    def test_login_user_with_invalid_details(self):
        url = reverse('login_user')
        response = self.client.post(url, self.login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

