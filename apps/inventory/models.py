from django.db import models
from django.conf import settings


class Product(models.Model):
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)

    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "sku"], name="unique_store_sku"),
        ]

    def __str__(self):
        return f"{self.name} ({self.store.name})"

class StockReceipt(models.Model):
    class PaymentStatus(models.TextChoices):
        PAID = "paid", "Paid"
        UNPAID = "unpaid", "Unpaid"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_receipts"
    )
    quantity_received = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    supplier_name = models.CharField(max_length=200, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stock_received"
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return self.quantity_received * self.unit_cost

    def __str__(self):
        return f"{self.quantity_received}x {self.product.name} ({self.payment_status})"


class SpoilageRecord(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="spoilage_records"
    )
    quantity_spoiled = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spoilage_recorded"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity_spoiled}x {self.product.name} spoiled"