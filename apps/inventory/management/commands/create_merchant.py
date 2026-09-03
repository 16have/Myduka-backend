from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User, StoreMembership
from apps.stores.models import Store


class Command(BaseCommand):
    help = "Create the initial merchant account and store for a fresh deployment."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== MyDuka Initial Setup ===\n"))

        # ── Store details ──────────────────────────────────────────────────
        store_name = input("Store name: ").strip()
        if not store_name:
            self.stderr.write(self.style.ERROR("Store name cannot be empty."))
            return

        store_location = input("Store location (optional): ").strip()
        store_phone = input("Store phone (optional): ").strip()

        # ── Merchant account ───────────────────────────────────────────────
        self.stdout.write("\n--- Merchant account ---")
        username = input("Username: ").strip()
        if not username:
            self.stderr.write(self.style.ERROR("Username cannot be empty."))
            return

        email = input("Email: ").strip().lower()
        if not email:
            self.stderr.write(self.style.ERROR("Email cannot be empty."))
            return

        if User.objects.filter(email=email).exists():
            self.stderr.write(self.style.ERROR(f"A user with email '{email}' already exists."))
            return

        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(f"Username '{username}' is already taken."))
            return

        import getpass
        while True:
            password = getpass.getpass("Password (min 8 chars): ")
            if len(password) < 8:
                self.stderr.write(self.style.ERROR("Password must be at least 8 characters."))
                continue
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                self.stderr.write(self.style.ERROR("Passwords do not match. Try again."))
                continue
            break

        # ── Create everything in one transaction ───────────────────────────
        with transaction.atomic():
            store = Store.objects.create(
                name=store_name,
                location=store_location,
                phone=store_phone,
            )

            merchant = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=User.Role.MERCHANT,
            )

            StoreMembership.objects.create(
                user=merchant,
                store=store,
                role=StoreMembership.Role.OWNER,
                is_primary=True,
            )

            merchant.primary_store = store
            merchant.save()

        self.stdout.write(self.style.SUCCESS(
            f"\n✔ Store '{store_name}' created."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"✔ Merchant account '{email}' created."
        ))
        self.stdout.write(self.style.SUCCESS(
            "\nYou can now log in at http://localhost:5173 and invite your admins.\n"
        ))
