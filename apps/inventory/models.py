from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Store


class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock_level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["store"])]

    def __str__(self):
        return self.name

    @property
    def stock_status(self) -> str:
        if self.current_stock == 0:
            return "Out of Stock"
        if self.current_stock <= self.minimum_stock_level:
            return "Low Stock"
        return "In Stock"


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    current_stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} inventory"


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        RECEIVED = "Received", "Received"
        SOLD = "Sold", "Sold"
        SPOILED = "Spoiled", "Spoiled"
        ADJUSTED = "Adjusted", "Adjusted"

    class PaymentStatus(models.TextChoices):
        PAID = "Paid", "Paid"
        NOT_PAID = "Not Paid", "Not Paid"

    reference_number = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_transactions")
    clerk = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    buying_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True
    )
    supplier = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_PAID,
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["transaction_type"]),
        ]

    def __str__(self):
        return self.reference_number


class SpoilageRecord(models.Model):
    class Reason(models.TextChoices):
        BROKEN = "Broken", "Broken"
        EXPIRED = "Expired", "Expired"
        OTHER = "Other", "Other"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="spoilage_records")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reason = models.CharField(max_length=20, choices=Reason.choices)
    notes = models.TextField(blank=True, null=True)
    recorder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="spoilage_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product} x{self.quantity} ({self.reason})"


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        DECLINED = "Declined", "Declined"
        ORDERED = "Ordered", "Ordered"
        RECEIVED = "Received", "Received"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="supply_requests")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reason = models.CharField(max_length=300)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_response = models.TextField(blank=True, null=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supply_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["requester"]),
        ]

    def __str__(self):
        return f"{self.product} x{self.quantity} ({self.status})"
