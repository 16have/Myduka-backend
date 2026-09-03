from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

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

class StoreInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"

    email = models.EmailField()
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="invites",
    )
    role = models.CharField(
        max_length=20,
        choices=[
            (StoreMembership.Role.ADMIN, "Store Admin"),
            (StoreMembership.Role.CLERK, "Data Entry Clerk"),
        ],
    )
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="invites_sent",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.status == self.Status.PENDING and timezone.now() < self.expires_at

    def __str__(self):
        return f"Invite: {self.email} → {self.store.name} ({self.role})"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_valid(self):
        expiry = self.created_at + timedelta(hours=1)
        return not self.used and timezone.now() < expiry

    def __str__(self):
        return f"Reset token for {self.user.username}"