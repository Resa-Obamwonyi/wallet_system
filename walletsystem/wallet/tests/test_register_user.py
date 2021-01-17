from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse


# Test User Registration Endpoint
class TestRegisterUser(APITestCase):
    def setUp(self):
        self.data = {
            "firstname": "Theresa",
            "lastname": "Obamwonyi",
            "email": "theresaobamwonyi@gmail.com",
            "password": "resa12345",
            "wallet_type": "Elite",
            "main_currency": "USD"
        }

    def test_register_user(self):
        url = reverse('register_user')
        response = self.client.post(url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_creates_user(self):
        url = reverse('register_user')
        response = self.client.post(url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('email'), 'theresaobamwonyi@gmail.com')
