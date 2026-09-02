from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store
from apps.inventory.models import Product
from apps.supply_requests.models import SupplyRequest


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
            "product": self.product.id, "quantity": 20, "reason": "Running low",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Pending")

    def test_clerk_cannot_update_status(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity": 20, "reason": "Running low",
        })
        request_id = create_response.data["id"]

        update_response = self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Approved"})
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_workflow_increases_stock_on_received(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity": 20, "reason": "Running low",
        })
        request_id = create_response.data["id"]

        self._login("owner@example.com", "Pass12345")

        approve_response = self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Approved"})
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        ordered_response = self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Ordered"})
        self.assertEqual(ordered_response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 50)  # no change yet — not Received

        received_response = self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Received"})
        self.assertEqual(received_response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 70)  # 50 + 20, only now

    def test_editing_received_request_does_not_double_increment_stock(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity": 20, "reason": "Running low",
        })
        request_id = create_response.data["id"]

        self._login("owner@example.com", "Pass12345")
        self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Received"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 70)

        # Edit admin_response on the already-Received request
        self.client.patch(f"/api/supply-requests/{request_id}/", {"admin_response": "Delivered on time"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 70)  # unchanged — no double-increment

    def test_declined_request_does_not_change_stock(self):
        self._login("clerk@example.com", "Pass12345")
        create_response = self.client.post("/api/supply-requests/", {
            "product": self.product.id, "quantity": 20, "reason": "Running low",
        })
        request_id = create_response.data["id"]

        self._login("owner@example.com", "Pass12345")
        decline_response = self.client.patch(f"/api/supply-requests/{request_id}/", {"status": "Declined"})
        self.assertEqual(decline_response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 50)