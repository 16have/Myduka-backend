from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store
from apps.inventory.models import Product
from apps.supply_requests.models import SupplyRequest
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache

@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": (
            "rest_framework.permissions.IsAuthenticated",
        ),
    }
)

class SupplyRequestWorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.store = Store.objects.create(name="Test Store")

        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="Pass12345",
        )
        StoreMembership.objects.create(user=self.owner, store=self.store, role="owner", is_primary=True)

        self.clerk = User.objects.create_user(
            username="clerk", email="clerk@example.com", password="Pass12345",
        )
        StoreMembership.objects.create(user=self.clerk, store=self.store, role="clerk", is_primary=True)

        self.product = Product.objects.create(
            store=self.store, name="Widget", sku="WID-001",
            buying_price=10, selling_price=15, quantity=50,
        )

    def _login(self, email, password):
        response = self.client.post("/api/token/", {"email": email, "password": password})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_clerk_can_create_supply_request(self):
        self._login("clerk@example.com", "Pass12345")
        response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity_requested": 20,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending")

    def test_clerk_cannot_approve_own_request(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity_requested": 20,
        })
        request_id = create_response.data["id"]

        approve_response = self.client.post(f"/api/supply-requests/{request_id}/approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_workflow_increases_stock_correctly(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity_requested": 20,
        })
        request_id = create_response.data["id"]

        # Switch to owner for approve + fulfill
        self._login("owner@example.com", "Pass12345")

        approve_response = self.client.post(f"/api/supply-requests/{request_id}/approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "approved")

        fulfill_response = self.client.post(f"/api/supply-requests/{request_id}/fulfill/")
        self.assertEqual(fulfill_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fulfill_response.data["status"], "fulfilled")

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 70)  # 50 + 20

    def test_cannot_fulfill_before_approval(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity_requested": 20,
        })
        request_id = create_response.data["id"]

        self._login("owner@example.com", "Pass12345")
        fulfill_response = self.client.post(f"/api/supply-requests/{request_id}/fulfill/")
        self.assertEqual(fulfill_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 50)  # unchanged

    def test_rejected_request_does_not_change_stock(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity_requested": 20,
        })
        request_id = create_response.data["id"]

        self._login("owner@example.com", "Pass12345")
        reject_response = self.client.post(f"/api/supply-requests/{request_id}/reject/")
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.data["status"], "rejected")

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 50)  # unchanged