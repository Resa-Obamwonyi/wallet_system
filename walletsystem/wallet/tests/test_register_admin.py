from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse


# Test User Registration Endpoint
class TestRegisterAdmin(APITestCase):
    def setUp(self):
        self.data = {
            "firstname":"Admin",
            "lastname": "User",
            "email": "testadmin@walletsystem.com",
            "password": "01234Admin"
        }

    def test_create_admin(self):
        url = reverse('register_admin')
        response = self.client.post(url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

