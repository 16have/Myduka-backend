from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, StoreMembership, StoreInvite
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


class InviteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.merchant = User.objects.create_user(
            username="merchant", email="merchant@example.com",
            password="TestPass123", role=User.Role.MERCHANT,
        )
        self.store = Store.objects.create(name="Test Store", location="Nairobi")
        StoreMembership.objects.create(
            user=self.merchant,
            store=self.store,
            role=StoreMembership.Role.OWNER,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.merchant)

    def test_create_invite_accepts_expires_in_hours(self):
        response = self.client.post("/api/accounts/invites/", {
            "email": "newadmin@example.com",
            "store_id": self.store.id,
            "role": StoreMembership.Role.ADMIN,
            "expires_in_hours": 1,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("expires_at", response.data)

    def test_delete_invite_requires_admin_or_owner(self):
        invite = StoreInvite.objects.create(
            email="clerk@example.com",
            store=self.store,
            role=StoreMembership.Role.CLERK,
            invited_by=self.merchant,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        response = self.client.delete(f"/api/accounts/invites/{invite.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StoreInvite.objects.filter(id=invite.id).exists())