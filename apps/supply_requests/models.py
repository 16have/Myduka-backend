from django.db import models
from django.conf import settings


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FULFILLED = "fulfilled", "Fulfilled"

    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.CASCADE,
        related_name="supply_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supply_requests_made",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supply_requests_reviewed",
    )
    quantity_requested = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} x{self.quantity_requested} ({self.status})"