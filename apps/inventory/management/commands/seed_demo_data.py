from django.core.management.base import BaseCommand
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store
from apps.inventory.models import Product


class Command(BaseCommand):
    help = "Seed the database with realistic test data for local development."

    def handle(self, *args, **options):
        if User.objects.filter(username="merchant_demo").exists():
            self.stdout.write(self.style.WARNING("Seed data already exists — skipping."))
            return

        merchant = User.objects.create_user(
            username="merchant_demo",
            email="merchant@myduka.test",
            password="TestPass123",
            role=User.Role.MERCHANT,
        )
        store = Store.objects.create(
            name="Kilimani Duka",
            location="Kilimani, Nairobi",
            phone="0722000001",
            email="kilimani@myduka.test",
        )
        StoreMembership.objects.create(user=merchant, store=store, role="owner", is_primary=True)
        merchant.primary_store = store
        merchant.save()

        admin = User.objects.create_user(
            username="admin_demo", email="admin@myduka.test",
            password="TestPass123", role=User.Role.ADMIN,
        )
        StoreMembership.objects.create(user=admin, store=store, role="admin", is_primary=True)

        clerk = User.objects.create_user(
            username="clerk_demo", email="clerk@myduka.test",
            password="TestPass123", role=User.Role.CLERK,
        )
        StoreMembership.objects.create(user=clerk, store=store, role="clerk", is_primary=True)

        products = [
            {"name": "Sukuma Wiki", "sku": "VEG-001", "category": "Vegetables",
             "buying_price": 15.00, "selling_price": 20.00, "quantity": 80, "low_stock_threshold": 20},
            {"name": "Unga wa Ngano 2kg", "sku": "FLR-001", "category": "Flour",
             "buying_price": 140.00, "selling_price": 170.00, "quantity": 45, "low_stock_threshold": 15},
            {"name": "Cooking Oil 1L", "sku": "OIL-001", "category": "Cooking Oil",
             "buying_price": 220.00, "selling_price": 260.00, "quantity": 8, "low_stock_threshold": 10},
            {"name": "Sugar 1kg", "sku": "SGR-001", "category": "Sugar",
             "buying_price": 130.00, "selling_price": 150.00, "quantity": 0, "low_stock_threshold": 10},
        ]
        for p in products:
            Product.objects.create(store=store, supplier_name="Local Wholesalers", **p)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: 1 store, 3 users (merchant/admin/clerk, all password TestPass123), {len(products)} products."
        ))
        self.stdout.write(self.style.SUCCESS(
            "Logins: merchant@myduka.test / admin@myduka.test / clerk@myduka.test"
        ))