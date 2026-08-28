from django.db import models


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