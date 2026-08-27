from decimal import Decimal

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Store, User
from apps.inventory.models import Product, StockTransaction


class ReportsApiTests(APITestCase):
    def setUp(self):
        self.merchant = User.objects.create_user(
            email="merchant@example.com", password="password123", name="Merchant", role=User.Role.MERCHANT
        )
        self.store = Store.objects.create(name="Main Store", merchant=self.merchant)
        self.merchant.store = self.store
        self.merchant.save(update_fields=["store"])
        self.clerk = User.objects.create_user(
            email="clerk@example.com", password="password123", name="Clerk", role=User.Role.CLERK, store=self.store
        )
        self.product = Product.objects.create(
            store=self.store,
            name="Sugar 2kg",
            buying_price=Decimal("150.00"),
            selling_price=Decimal("200.00"),
            current_stock=10,
        )
        StockTransaction.objects.create(
            product=self.product,
            clerk=self.clerk,
            transaction_type=StockTransaction.TransactionType.SOLD,
            quantity=3,
            selling_price=Decimal("200.00"),
            payment_status="Paid",
            reference_number="SLD-0001",
        )

        token = AccessToken.for_user(self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_unauthenticated_request_is_rejected(self):
        self.client.credentials()
        response = self.client.get("/api/v1/reports/inventory/")
        self.assertEqual(response.status_code, 401)

    def test_inventory_report(self):
        response = self.client.get("/api/v1/reports/inventory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_products"], 1)
        self.assertEqual(response.data["data"][0]["sold_qty"], 3)

    def test_product_performance_report(self):
        response = self.client.get("/api/v1/reports/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"][0]["total_quantity"], 3)
        self.assertEqual(response.data["data"][0]["total_revenue"], "600.00")

    def test_store_performance_report(self):
        response = self.client.get("/api/v1/reports/stores/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"][0]["total_sales"], "600.00")

    def test_clerk_performance_report(self):
        response = self.client.get("/api/v1/reports/clerks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"][0]["clerk_name"], "Clerk")

    def test_invalid_period_returns_400(self):
        response = self.client.get("/api/v1/reports/inventory/?period=daily")
        self.assertEqual(response.status_code, 400)

    def test_monthly_and_annual_periods(self):
        for period in ("monthly", "annual"):
            response = self.client.get(f"/api/v1/reports/inventory/?period={period}")
            self.assertEqual(response.status_code, 200)
