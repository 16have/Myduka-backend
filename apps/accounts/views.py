import os

from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import User, StoreInvite, StoreMembership, PasswordResetToken
from apps.stores.models import Store
from .serializers import (
    MerchantRegistrationSerializer,
    CreateInviteSerializer,
    AcceptInviteSerializer,
    EmailTokenObtainPairSerializer,
    StoreMemberSerializer,
    RequestPasswordResetSerializer,
    ConfirmPasswordResetSerializer,
)


class MerchantRegistrationView(generics.GenericAPIView):
    serializer_class = MerchantRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "user": {
                    "id": result["user"].id,
                    "username": result["user"].username,
                    "email": result["user"].email,
                    "role": result["user"].role,
                },
                "store": {
                    "id": result["store"].id,
                    "name": result["store"].name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CreateInviteView(generics.GenericAPIView):
    serializer_class = CreateInviteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            store = Store.objects.get(id=data["store_id"])
        except Store.DoesNotExist:
            raise NotFound("Store not found.")

        membership = StoreMembership.objects.filter(
            user=request.user, store=store
        ).first()
        if not membership or membership.role not in ("owner", "admin"):
            raise PermissionDenied("Only store owners/admins can invite users.")

        invite = StoreInvite.objects.create(
            email=data["email"],
            store=store,
            role=data["role"],
            invited_by=request.user,
        )

        invite_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/accept-invite?token={invite.token}"
        send_mail(
            subject=f"You've been invited to join {store.name} on MyDuka",
            message=(
                f"You've been invited to join {store.name} as a {invite.role}.\n\n"
                f"Click the link to set up your account: {invite_link}\n\n"
                f"This invite expires on {invite.expires_at.strftime('%Y-%m-%d')}."
            ),
            from_email=None,
            recipient_list=[invite.email],
        )

        return Response(
            {
                "id": invite.id,
                "email": invite.email,
                "token": str(invite.token),
                "store": store.name,
                "role": invite.role,
                "status": invite.status,
                "created_at": invite.created_at,
                "expires_at": invite.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class AcceptInviteView(generics.GenericAPIView):
    serializer_class = AcceptInviteSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "user": {
                    "id": result["user"].id,
                    "username": result["user"].username,
                    "email": result["user"].email,
                    "role": result["user"].role,
                },
                "store": {"id": result["store"].id, "name": result["store"].name},
            },
            status=status.HTTP_201_CREATED,
        )


class ValidateInviteView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("token", OpenApiTypes.UUID, OpenApiParameter.QUERY)],
        responses={200: dict},
    )
    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response({"detail": "Missing token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invite = StoreInvite.objects.get(token=token)
        except StoreInvite.DoesNotExist:
            raise NotFound("This invitation link is invalid.")

        if invite.status != StoreInvite.Status.PENDING:
            return Response(
                {"detail": "This invitation has already been used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not invite.is_valid():
            return Response(
                {"detail": "This invitation has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "email": invite.email,
            "role": invite.role,
            "store": invite.store.name,
        })


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class StoreMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/accounts/members/?store_id=2&role=clerk
    """
    serializer_class = StoreMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: StoreMemberSerializer})
    def get_queryset(self):
        managed_store_ids = StoreMembership.objects.filter(
            user=self.request.user, role__in=["owner", "admin"]
        ).values_list("store_id", flat=True)

        qs = StoreMembership.objects.filter(store_id__in=managed_store_ids)

        store_id = self.request.query_params.get("store_id")
        if store_id:
            qs = qs.filter(store_id=store_id)

        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        return qs.exclude(role="owner")


class ToggleMemberActiveView(generics.GenericAPIView):
    """
    POST /api/accounts/members/{membership_id}/toggle-active/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, membership_id):
        try:
            membership = StoreMembership.objects.get(id=membership_id)
        except StoreMembership.DoesNotExist:
            raise NotFound("Membership not found.")

        requester_membership = StoreMembership.objects.filter(
            user=request.user, store=membership.store, role__in=["owner", "admin"]
        ).first()
        if not requester_membership:
            raise PermissionDenied("Only store owners/admins can manage members.")

        if membership.role == "owner":
            raise PermissionDenied("Cannot deactivate a store owner.")

        target_user = membership.user
        target_user.is_active = not target_user.is_active
        target_user.save()

        return Response(StoreMemberSerializer(membership).data)


class RemoveMemberView(generics.GenericAPIView):
    """
    DELETE /api/accounts/members/{membership_id}/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    @extend_schema(responses={204: None})
    def delete(self, request, membership_id):
        try:
            membership = StoreMembership.objects.get(id=membership_id)
        except StoreMembership.DoesNotExist:
            raise NotFound("Membership not found.")

        requester_membership = StoreMembership.objects.filter(
            user=request.user, store=membership.store, role__in=["owner", "admin"]
        ).first()
        if not requester_membership:
            raise PermissionDenied("Only store owners/admins can remove members.")

        if membership.role == "owner":
            raise PermissionDenied("Cannot remove a store owner.")

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PendingInvitesView(generics.ListAPIView):
    """
    GET /api/accounts/invites/pending/?store_id=2
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    @extend_schema(
        parameters=[OpenApiParameter("store_id", OpenApiTypes.INT, OpenApiParameter.QUERY)],
        responses={200: dict},
    )
    def list(self, request):
        managed_store_ids = StoreMembership.objects.filter(
            user=request.user, role__in=["owner", "admin"]
        ).values_list("store_id", flat=True)

        qs = StoreInvite.objects.filter(
            store_id__in=managed_store_ids, status=StoreInvite.Status.PENDING
        )
        store_id = request.query_params.get("store_id")
        if store_id:
            qs = qs.filter(store_id=store_id)

        data = [
            {
                "id": inv.id,
                "email": inv.email,
                "token": str(inv.token),
                "role": inv.role,
                "store": inv.store.name,
                "status": inv.status,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            }
            for inv in qs
        ]
        return Response(data)


class RequestPasswordResetView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.create(user=user)
            reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password?token={reset_token.token}"
            send_mail(
                subject="Reset your MyDuka password",
                message=f"Click the link to reset your password: {reset_link}\n\nThis link expires in 1 hour.",
                from_email=None,
                recipient_list=[email],
            )
        except User.DoesNotExist:
            pass

        return Response(
            {"detail": "If an account with that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ConfirmPasswordResetView(generics.GenericAPIView):
    serializer_class = ConfirmPasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password reset successful. You can now log in."})
