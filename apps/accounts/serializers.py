from rest_framework import serializers
from django.db import transaction
from .models import User, StoreMembership
from apps.stores.models import Store
from .models import StoreInvite
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import PasswordResetToken


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
    
class CreateInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    store_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=[StoreMembership.Role.ADMIN, StoreMembership.Role.CLERK])


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_token(self, value):
        try:
            invite = StoreInvite.objects.get(token=value)
        except StoreInvite.DoesNotExist:
            raise serializers.ValidationError("Invalid invite token.")
        if not invite.is_valid():
            raise serializers.ValidationError("This invite has expired or was already used.")
        if User.objects.filter(email=invite.email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Please log in instead."
            )
        self.invite = invite
        return value

    def create(self, validated_data):
        invite = self.invite
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=invite.email,
                password=validated_data["password"],
                role=invite.role,
            )
            StoreMembership.objects.create(
                user=user,
                store=invite.store,
                role=invite.role,
                is_primary=True,
            )
            invite.status = StoreInvite.Status.ACCEPTED
            invite.save()

        return {"user": user, "store": invite.store}   

class StoreMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    name = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    membership_id = serializers.IntegerField(source="id", read_only=True)
    created_at = serializers.DateTimeField(source="user.date_joined", read_only=True)

    class Meta:
        model = StoreMembership
        fields = ["membership_id", "id", "username", "name", "email", "role", "is_active", "is_primary", "created_at"]

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = serializers.EmailField()
        self.fields.pop(self.username_field, None)

    def validate(self, attrs):
        email = attrs.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active account found with the given credentials")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Contact your administrator.")

        attrs[self.username_field] = user.get_username()
        data = super().validate(attrs)

        # Primary store: prefer explicit primary_store, fall back to first membership
        store_id = None
        store_name = None
        if user.primary_store:
            store_id = user.primary_store.id
            store_name = user.primary_store.name
        else:
            membership = user.store_memberships.select_related("store").first()
            if membership:
                store_id = membership.store.id
                store_name = membership.store.name

        data["user"] = {
            "id": user.id,
            "username": user.username,
            "name": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "store_id": store_id,
            "store_name": store_name,
        }
        return data

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_token(self, value):
        try:
            reset_token = PasswordResetToken.objects.get(token=value)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token.")
        if not reset_token.is_valid():
            raise serializers.ValidationError("This reset link has expired or was already used.")
        self.reset_token = reset_token
        return value

    def save(self):
        reset_token = self.reset_token
        user = reset_token.user
        user.set_password(self.validated_data["new_password"])
        user.save()
        reset_token.used = True
        reset_token.save()
        return user