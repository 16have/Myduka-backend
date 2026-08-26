from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Invitation, User


class UserSerializer(serializers.ModelSerializer):
    store_id = serializers.IntegerField(source="store.id", read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "is_active", "created_at", "store_id")


class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")
        user = authenticate(self.context.get("request"), email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Unable to log in with those credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Contact your administrator.")
        refresh = self.get_token(user)
        return {"access_token": str(refresh.access_token), "refresh_token": str(refresh), "user": UserSerializer(user).data}


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