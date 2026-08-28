from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .serializers import MerchantRegistrationSerializer
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.exceptions import PermissionDenied, NotFound
from .models import StoreInvite, StoreMembership
from apps.stores.models import Store
from .serializers import CreateInviteSerializer, AcceptInviteSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import EmailTokenObtainPairSerializer
from rest_framework import viewsets
from .models import StoreMembership
from .serializers import StoreMemberSerializer
from apps.stores.models import Store


class MerchantRegistrationView(generics.GenericAPIView):
    serializer_class = MerchantRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # public — this IS the signup endpoint

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

        invite_link = f"http://localhost:5173/accept-invite?token={invite.token}"
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
                "store": store.name,
                "role": invite.role,
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

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer  

class StoreMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List members (admins/clerks) of stores the requester owns/admins.
    GET /api/accounts/members/?store_id=2&role=clerk
    """
    serializer_class = StoreMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only stores where the requester is owner/admin
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

        return qs.exclude(role="owner")  # owners aren't "managed" — they're the manager


class ToggleMemberActiveView(generics.GenericAPIView):
    """
    POST /api/accounts/members/{membership_id}/toggle-active/
    Activates/deactivates the underlying User (not the membership itself).
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
    Removes the StoreMembership (does not delete the User account itself,
    since they may belong to other stores).
    """
    permission_classes = [permissions.IsAuthenticated]

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
                "role": inv.role,
                "store": inv.store.name,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            }
            for inv in qs
        ]
        return Response(data)