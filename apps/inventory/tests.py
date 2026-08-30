from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store
from apps.inventory.models import Product
from django.core.cache import cache


class ProductAccessControlTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Store A, owned by user_a
        self.store_a = Store.objects.create(name="Store A")
        self.user_a = User.objects.create_user(
            username="usera", email="usera@example.com", password="Pass12345",
        )
        StoreMembership.objects.create(user=self.user_a, store=self.store_a, role="owner", is_primary=True)
        self.product_a = Product.objects.create(
            store=self.store_a, name="Product A", sku="A-001",
            buying_price=10, selling_price=15, quantity=50,
        )

        # Store B, owned by user_b — completely separate
        self.store_b = Store.objects.create(name="Store B")
        self.user_b = User.objects.create_user(
            username="userb", email="userb@example.com", password="Pass12345",
        )
        StoreMembership.objects.create(user=self.user_b, store=self.store_b, role="owner", is_primary=True)
        self.product_b = Product.objects.create(
            store=self.store_b, name="Product B", sku="B-001",
            buying_price=20, selling_price=25, quantity=30,
        )

    def _login(self, email, password):
        response = self.client.post("/api/token/", {"email": email, "password": password})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_user_only_sees_own_store_products(self):
        self._login("usera@example.com", "Pass12345")
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_ids = [p["id"] for p in response.data]
        self.assertIn(self.product_a.id, product_ids)
        self.assertNotIn(self.product_b.id, product_ids)

    def test_user_cannot_view_other_store_product_directly(self):
        self._login("usera@example.com", "Pass12345")
        response = self.client.get(f"/api/products/{self.product_b.id}/")
        # Filtered queryset means it's not "found" for this user at all
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_create_product_for_other_store(self):
        self._login("usera@example.com", "Pass12345")
        response = self.client.post("/api/products/", {
            "store": self.store_b.id, "name": "Sneaky Product",
            "sku": "SNEAKY-001", "buying_price": 5, "selling_price": 10, "quantity": 1,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_create_product_for_own_store(self):
        self._login("usera@example.com", "Pass12345")
        response = self.client.post("/api/products/", {
            "store": self.store_a.id, "name": "New Product",
            "sku": "NEW-001", "buying_price": 5, "selling_price": 10, "quantity": 20,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_stock_status_computed_correctly(self):
        low_stock_product = Product.objects.create(
            store=self.store_a, name="Low Stock Item", sku="LOW-001",
            buying_price=5, selling_price=10, quantity=3, low_stock_threshold=10,
        )
        out_of_stock_product = Product.objects.create(
            store=self.store_a, name="Out of Stock Item", sku="OUT-001",
            buying_price=5, selling_price=10, quantity=0,
        )
        self.assertEqual(low_stock_product.stock_status, Product.StockStatus.LOW_STOCK)
        self.assertEqual(out_of_stock_product.stock_status, Product.StockStatus.OUT_OF_STOCK)
        self.assertEqual(self.product_a.stock_status, Product.StockStatus.IN_STOCK)