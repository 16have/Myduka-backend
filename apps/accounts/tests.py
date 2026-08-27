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

	def test_login_rejects_wrong_password(self):
		response = self.client.post("/api/auth/login", {"email": "merchant@example.com", "password": "wrong"})
		self.assertEqual(response.status_code, 401)

	def test_login_rejects_deactivated_account(self):
		self.admin.is_active = False
		self.admin.save(update_fields=["is_active"])
		response = self.client.post("/api/auth/login", {"email": "admin@example.com", "password": "password123"})
		self.assertEqual(response.status_code, 403)
		self.assertIn("deactivated", response.data["detail"])

	def test_logout_requires_authentication(self):
		response = self.client.post("/api/auth/logout")
		self.assertEqual(response.status_code, 401)

	def test_authenticated_logout_succeeds(self):
		self.authenticate(self.merchant)
		response = self.client.post("/api/auth/logout")
		self.assertEqual(response.status_code, 204)

	def test_me_returns_current_user(self):
		self.authenticate(self.admin)
		response = self.client.get("/api/auth/me")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["email"], "admin@example.com")

	def test_invitation_to_existing_email_is_rejected(self):
		self.authenticate(self.merchant)
		response = self.client.post("/api/auth/invitations", {"email": "admin@example.com"})
		self.assertEqual(response.status_code, 400)

	def test_duplicate_pending_invitation_is_rejected(self):
		self.authenticate(self.merchant)
		self.client.post("/api/auth/invitations", {"email": "newadmin@example.com"})
		response = self.client.post("/api/auth/invitations", {"email": "newadmin@example.com"})
		self.assertEqual(response.status_code, 400)

	def test_admin_cannot_send_invitations(self):
		self.authenticate(self.admin)
		response = self.client.post("/api/auth/invitations", {"email": "someone@example.com"})
		self.assertEqual(response.status_code, 403)

	def test_invalid_invitation_token_is_rejected(self):
		response = self.client.get("/api/auth/invitations/does-not-exist")
		self.assertEqual(response.status_code, 404)

	def test_register_admin_with_invalid_token_fails(self):
		response = self.client.post(
			"/api/auth/register-admin", {"token": "bad-token", "name": "Nobody", "password": "MyDukaTestPassword#2026"}
		)
		self.assertEqual(response.status_code, 400)

	def test_merchant_can_list_admins(self):
		self.authenticate(self.merchant)
		response = self.client.get("/api/auth/admins")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["email"], "admin@example.com")

	def test_clerk_cannot_list_admins(self):
		self.authenticate(self.admin)
		response = self.client.get("/api/auth/admins")
		self.assertEqual(response.status_code, 403)

	def test_admin_can_list_clerks(self):
		self.authenticate(self.admin)
		self.client.post("/api/auth/clerks", {"name": "Clerk One", "email": "clerk1@example.com"})
		response = self.client.get("/api/auth/clerks")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)

	def test_create_clerk_requires_valid_name(self):
		self.authenticate(self.admin)
		response = self.client.post("/api/auth/clerks", {"name": "X", "email": "clerk2@example.com"})
		self.assertEqual(response.status_code, 400)

	def test_create_clerk_rejects_duplicate_email(self):
		self.authenticate(self.admin)
		response = self.client.post("/api/auth/clerks", {"name": "Clerk Two", "email": "admin@example.com"})
		self.assertEqual(response.status_code, 400)

	def test_merchant_can_deactivate_and_reactivate_admin(self):
		self.authenticate(self.merchant)
		response = self.client.patch(f"/api/auth/admins/{self.admin.id}/deactivate")
		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.data["is_active"])

		response = self.client.patch(f"/api/auth/admins/{self.admin.id}/activate")
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["is_active"])

	def test_user_action_rejects_unknown_action(self):
		self.authenticate(self.merchant)
		response = self.client.patch(f"/api/auth/admins/{self.admin.id}/nonsense")
		self.assertEqual(response.status_code, 400)

	def test_user_action_returns_404_for_missing_user(self):
		self.authenticate(self.merchant)
		response = self.client.patch("/api/auth/admins/999999/activate")
		self.assertEqual(response.status_code, 404)

	def test_admin_can_deactivate_clerk_but_not_another_admin(self):
		self.authenticate(self.admin)
		create = self.client.post("/api/auth/clerks", {"name": "Clerk Three", "email": "clerk3@example.com"})
		clerk_id = create.data["user"]["id"]

		response = self.client.patch(f"/api/auth/clerks/{clerk_id}/deactivate")
		self.assertEqual(response.status_code, 200)

		response = self.client.patch(f"/api/auth/admins/{self.admin.id}/deactivate")
		self.assertEqual(response.status_code, 404)

	def test_merchant_can_delete_admin(self):
		self.authenticate(self.merchant)
		response = self.client.delete(f"/api/auth/admins/{self.admin.id}/delete")
		self.assertEqual(response.status_code, 204)
		self.assertFalse(User.objects.filter(id=self.admin.id).exists())

	def test_delete_missing_user_returns_404(self):
		self.authenticate(self.merchant)
		response = self.client.delete("/api/auth/admins/999999/delete")
		self.assertEqual(response.status_code, 404)
