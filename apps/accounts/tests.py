from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store
from django.core.cache import cache


class AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com",
            password="TestPass123", role=User.Role.MERCHANT,
        )

    def test_login_with_correct_credentials_succeeds(self):
        response = self.client.post("/api/token/", {
            "email": "test@example.com", "password": "TestPass123",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "test@example.com")

    def test_login_with_wrong_password_fails(self):
        response = self.client.post("/api/token/", {
            "email": "test@example.com", "password": "WrongPassword",
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_nonexistent_email_fails(self):
        response = self.client.post("/api/token/", {
            "email": "nobody@example.com", "password": "whatever",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivated_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post("/api/token/", {
            "email": "test@example.com", "password": "TestPass123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            

    def test_unauthenticated_request_to_protected_endpoint_fails(self):
        response = self.client.get("/api/stores/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MerchantRegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_registration_creates_user_store_and_membership(self):
        response = self.client.post("/api/accounts/register/", {
            "username": "newmerchant", "email": "new@example.com",
            "password": "SecurePass123", "store_name": "New Duka",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="newmerchant")
        self.assertEqual(user.role, User.Role.MERCHANT)

        membership = StoreMembership.objects.get(user=user)
        self.assertEqual(membership.role, "owner")
        self.assertTrue(membership.is_primary)

    def test_registration_with_duplicate_email_fails(self):
        User.objects.create_user(
            username="existing", email="taken@example.com", password="pass12345",
        )
        response = self.client.post("/api/accounts/register/", {
            "username": "another", "email": "taken@example.com",
            "password": "SecurePass123", "store_name": "Another Duka",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)