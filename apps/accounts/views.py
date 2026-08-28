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