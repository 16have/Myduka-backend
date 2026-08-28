from rest_framework import serializers
from django.db import transaction
from .models import User, StoreMembership
from apps.stores.models import Store


class MerchantRegistrationSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    # Store fields (created alongside the user)
    store_name = serializers.CharField(max_length=150)
    store_location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    store_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    store_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                role=User.Role.MERCHANT,
            )

            store = Store.objects.create(
                name=validated_data["store_name"],
                location=validated_data.get("store_location", ""),
                phone=validated_data.get("store_phone", ""),
                email=validated_data.get("store_email", ""),
            )

            StoreMembership.objects.create(
                user=user,
                store=store,
                role=StoreMembership.Role.OWNER,
                is_primary=True,
            )

            user.primary_store = store
            user.save()

        return {"user": user, "store": store}