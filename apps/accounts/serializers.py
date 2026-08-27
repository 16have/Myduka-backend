from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Invitation, User


class UserSerializer(serializers.ModelSerializer):
    store_id = serializers.IntegerField(source="store.id", read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "is_active", "created_at", "store_id")


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenPairSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()


class DetailMessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class InviteEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class InvitationEmailLookupSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)


class ClerkCreateSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2)
    email = serializers.EmailField()


class ClerkCreateResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    temporaryPassword = serializers.CharField()


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ("id", "email", "token", "status", "created_at", "expires_at")
        read_only_fields = fields


class AdminRegistrationSerializer(serializers.Serializer):
    token = serializers.CharField()
    name = serializers.CharField(min_length=2, max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        try:
            invitation = Invitation.objects.select_related("store").get(token=attrs["token"])
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("This invitation link is invalid.")
        invitation.refresh_status()
        if invitation.status == Invitation.Status.USED:
            raise serializers.ValidationError("This invitation has already been used.")
        if invitation.status == Invitation.Status.EXPIRED:
            raise serializers.ValidationError("This invitation has expired.")
        validate_password(attrs["password"])
        attrs["invitation"] = invitation
        attrs["name"] = attrs["name"].strip()
        return attrs

    def save(self):
        invitation = self.validated_data["invitation"]
        user = User.objects.create_user(
            email=invitation.email,
            password=self.validated_data["password"],
            name=self.validated_data["name"],
            role=User.Role.ADMIN,
            store=invitation.store,
        )
        invitation.status = Invitation.Status.USED
        invitation.save(update_fields=["status"])
        return user