from django.contrib.auth.models import AbstractUser
from django.db import models


class StoreMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Store Admin"
        CLERK = "clerk", "Data Entry Clerk"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="store_memberships",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "store"], name="unique_user_store"),
        ]

    def __str__(self):
        return f"{self.user.username} – {self.store.name} ({self.role})"


class User(AbstractUser):
    class Role(models.TextChoices):
        MERCHANT = "merchant", "Merchant"
        ADMIN = "admin", "Store Admin"
        CLERK = "clerk", "Data Entry Clerk"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)

    primary_store = models.ForeignKey(
        "stores.Store",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_users",
    )

    def __str__(self):
        return f"{self.username} ({self.role})"