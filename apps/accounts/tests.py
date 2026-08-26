from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import Invitation, Store, User


class AuthenticationApiTests(APITestCase):
	def setUp(self):
		self.merchant = User.objects.create_user(
			email="merchant@example.com", password="password123", name="Merchant", role=User.Role.MERCHANT
		)
		self.store = Store.objects.create(name="Main Store", merchant=self.merchant)
		self.merchant.store = self.store
		self.merchant.save(update_fields=["store"])
		self.admin = User.objects.create_user(
			email="admin@example.com", password="password123", name="Admin", role=User.Role.ADMIN, store=self.store
		)

	def authenticate(self, user):
		token = AccessToken.for_user(user)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def test_login_returns_jwt_and_public_user(self):
		response = self.client.post("/api/auth/login", {"email": "MERCHANT@example.com", "password": "password123"})

		self.assertEqual(response.status_code, 200)
		self.assertIn("access_token", response.data)
		self.assertEqual(response.data["user"]["role"], User.Role.MERCHANT)
		self.assertNotIn("password", response.data["user"])

	def test_merchant_can_invite_and_register_admin_once(self):
		self.authenticate(self.merchant)
		response = self.client.post("/api/auth/invitations", {"email": "newadmin@example.com"})
		token = response.data["token"]

		registration = self.client.post(
			"/api/auth/register-admin", {"token": token, "name": "New Admin", "password": "MyDukaTestPassword#2026"}
		)
		duplicate = self.client.post(
			"/api/auth/register-admin", {"token": token, "name": "Again", "password": "MyDukaTestPassword#2026"}
		)

		self.assertEqual(registration.status_code, 201)
		self.assertEqual(duplicate.status_code, 400)
		self.assertTrue(User.objects.filter(email="newadmin@example.com", store=self.store).exists())

	def test_admin_can_create_clerk_in_their_store(self):
		self.authenticate(self.admin)
		response = self.client.post("/api/auth/clerks", {"name": "Clerk One", "email": "clerk@example.com"})

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["user"]["role"], User.Role.CLERK)
		self.assertTrue(response.data["temporaryPassword"])

	def test_expired_invitation_is_rejected(self):
		invitation = Invitation.objects.create(
			email="expired@example.com",
			token="expired-token",
			invited_by=self.merchant,
			store=self.store,
			expires_at=timezone.now() - timedelta(minutes=1),
		)

		response = self.client.get(f"/api/auth/invitations/{invitation.token}")

		self.assertEqual(response.status_code, 400)
