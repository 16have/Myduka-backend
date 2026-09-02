from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    supply_request = models.ForeignKey(
        "supply_requests.SupplyRequest",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.supply_request} — {self.status}"