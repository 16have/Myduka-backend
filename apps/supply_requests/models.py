from django.db import models
from django.conf import settings


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        DECLINED = "Declined", "Declined"
        ORDERED = "Ordered", "Ordered"
        RECEIVED = "Received", "Received"

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
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    admin_response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} x{self.quantity_requested} ({self.status})"