from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class MyUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email address is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.MERCHANT)
        extra_fields.setdefault("name", email.split("@", 1)[0])
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class Store(models.Model):
    name = models.CharField(max_length=255)
    merchant = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="owned_stores",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        MERCHANT = "merchant", "Merchant"
        ADMIN = "admin", "Store Admin"
        CLERK = "clerk", "Data Entry Clerk"

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="members",
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = MyUserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"

    email = models.EmailField()
    token = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invitations_sent",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="invitations",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.status})"

    def refresh_status(self):
        if self.status == self.Status.PENDING and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status"])
        return self.status