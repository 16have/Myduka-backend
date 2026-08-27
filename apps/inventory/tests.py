from decimal import Decimal

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Store, User

from .models import Product, SpoilageRecord, StockTransaction, SupplyRequest


class InventoryApiTestCase(APITestCase):
    def setUp(self):
        self.merchant = User.objects.create_user(
            email="merchant@example.com", password="password123", name="Merchant", role=User.Role.MERCHANT
        )
        self.store = Store.objects.create(name="Main Store", merchant=self.merchant)
        self.admin = User.objects.create_user(
            email="admin@example.com", password="password123", name="Admin", role=User.Role.ADMIN, store=self.store
        )
        self.clerk = User.objects.create_user(
            email="clerk@example.com", password="password123", name="Clerk", role=User.Role.CLERK, store=self.store
        )

        self.other_store = Store.objects.create(name="Other Store", merchant=self.merchant)
        self.other_admin = User.objects.create_user(
            email="other-admin@example.com",
            password="password123",
            name="Other Admin",
            role=User.Role.ADMIN,
            store=self.other_store,
        )

        self.product = Product.objects.create(
            store=self.store,
            name="Sugar 2kg",
            buying_price=Decimal("150.00"),
            selling_price=Decimal("200.00"),
            current_stock=10,
            minimum_stock_level=5,
        )

    def authenticate(self, user):
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class ProductApiTests(InventoryApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/inventory")
        self.assertEqual(response.status_code, 401)

    def test_clerk_can_list_products_in_their_store(self):
        self.authenticate(self.clerk)
        response = self.client.get("/api/inventory")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Sugar 2kg")

    def test_products_are_scoped_to_the_caller_store(self):
        self.authenticate(self.other_admin)
        response = self.client.get("/api/inventory")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])

    def test_admin_can_create_product(self):
        self.authenticate(self.admin)
        response = self.client.post(
            "/api/inventory",
            {"name": "Rice 5kg", "buying_price": "400.00", "selling_price": "550.00"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["store"], self.store.id)
        self.assertTrue(Product.objects.filter(name="Rice 5kg", store=self.store).exists())

    def test_clerk_cannot_create_product(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/inventory",
            {"name": "Rice 5kg", "buying_price": "400.00", "selling_price": "550.00"},
        )
        self.assertEqual(response.status_code, 403)

    def test_get_product_from_another_store_is_not_found(self):
        self.authenticate(self.other_admin)
        response = self.client.get(f"/api/inventory/{self.product.id}")
        self.assertEqual(response.status_code, 404)


class ReceiveStockApiTests(InventoryApiTestCase):
    def test_clerk_can_receive_stock(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/stock/receive",
            {
                "product_id": self.product.id,
                "quantity": 5,
                "buying_price": "150.00",
                "selling_price": "200.00",
                "payment_status": "Paid",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["new_stock_level"], 15)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 15)
        self.assertEqual(
            StockTransaction.objects.filter(transaction_type=StockTransaction.TransactionType.RECEIVED).count(), 1
        )

    def test_receive_stock_requires_all_fields(self):
        self.authenticate(self.clerk)
        response = self.client.post("/api/stock/receive", {"product_id": self.product.id, "quantity": 5})
        self.assertEqual(response.status_code, 400)

    def test_list_received_stock(self):
        self.authenticate(self.clerk)
        self.client.post(
            "/api/stock/receive",
            {
                "product_id": self.product.id,
                "quantity": 5,
                "buying_price": "150.00",
                "selling_price": "200.00",
                "payment_status": "Paid",
            },
        )
        response = self.client.get("/api/stock/received")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)


class SellStockApiTests(InventoryApiTestCase):
    def test_clerk_can_sell_stock(self):
        self.authenticate(self.clerk)
        response = self.client.post("/api/stock/sell", {"product_id": self.product.id, "quantity": 4})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["new_stock_level"], 6)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 6)
        txn = StockTransaction.objects.get(transaction_type=StockTransaction.TransactionType.SOLD)
        self.assertEqual(txn.selling_price, self.product.selling_price)

    def test_cannot_sell_more_than_available_stock(self):
        self.authenticate(self.clerk)
        response = self.client.post("/api/stock/sell", {"product_id": self.product.id, "quantity": 999})
        self.assertEqual(response.status_code, 409)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)


class SpoilageApiTests(InventoryApiTestCase):
    def test_clerk_can_record_spoilage(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/spoilage", {"product_id": self.product.id, "quantity": 2, "reason": "Broken"}
        )
        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 8)
        self.assertEqual(SpoilageRecord.objects.count(), 1)

    def test_invalid_reason_is_rejected(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/spoilage", {"product_id": self.product.id, "quantity": 2, "reason": "Stolen"}
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_spoil_more_than_available_stock(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/spoilage", {"product_id": self.product.id, "quantity": 999, "reason": "Broken"}
        )
        self.assertEqual(response.status_code, 409)


class SupplyRequestApiTests(InventoryApiTestCase):
    def test_clerk_can_create_and_list_supply_request(self):
        self.authenticate(self.clerk)
        response = self.client.post(
            "/api/supply-requests",
            {"product_id": self.product.id, "quantity": 20, "reason": "Running low ahead of the weekend."},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["status"], "Pending")

        listing = self.client.get("/api/supply-requests")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]), 1)

    def test_clerk_cannot_approve_supply_request(self):
        request_obj = SupplyRequest.objects.create(
            product=self.product, requester=self.clerk, quantity=10, reason="Restock"
        )
        self.authenticate(self.clerk)
        response = self.client.put(f"/api/supply-requests/{request_obj.id}", {"status": "Approved"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_supply_request(self):
        request_obj = SupplyRequest.objects.create(
            product=self.product, requester=self.clerk, quantity=10, reason="Restock"
        )
        self.authenticate(self.admin)
        response = self.client.put(f"/api/supply-requests/{request_obj.id}", {"status": "Approved"})
        self.assertEqual(response.status_code, 200)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, "Approved")

    def test_cannot_re_decide_a_resolved_request(self):
        request_obj = SupplyRequest.objects.create(
            product=self.product,
            requester=self.clerk,
            quantity=10,
            reason="Restock",
            status=SupplyRequest.Status.APPROVED,
        )
        self.authenticate(self.admin)
        response = self.client.put(f"/api/supply-requests/{request_obj.id}", {"status": "Declined"})
        self.assertEqual(response.status_code, 409)


class PaymentsApiTests(InventoryApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate(self.clerk)
        self.client.post(
            "/api/stock/receive",
            {
                "product_id": self.product.id,
                "quantity": 5,
                "buying_price": "150.00",
                "selling_price": "200.00",
                "payment_status": "Not Paid",
            },
        )
        self.txn = StockTransaction.objects.get(payment_status="Not Paid")

    def test_list_unpaid_payments(self):
        response = self.client.get("/api/payments/unpaid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_clerk_cannot_update_payment_status(self):
        response = self.client.put(f"/api/payments/{self.txn.id}/status", {"payment_status": "Paid"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_payment_status(self):
        self.authenticate(self.admin)
        response = self.client.put(f"/api/payments/{self.txn.id}/status", {"payment_status": "Paid"})
        self.assertEqual(response.status_code, 200)
        self.txn.refresh_from_db()
        self.assertEqual(self.txn.payment_status, "Paid")


class InventoryStatsApiTests(InventoryApiTestCase):
    def test_inventory_stats(self):
        Product.objects.create(
            store=self.store, name="Out of stock item", buying_price="10.00", selling_price="15.00", current_stock=0
        )
        self.authenticate(self.admin)
        response = self.client.get("/api/inventory/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total_products"], 2)
        self.assertEqual(response.data["data"]["out_of_stock"], 1)
