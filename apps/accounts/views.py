import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Invitation, User
from .permissions import IsMerchant, IsStoreAdmin
from .serializers import (
	AdminRegistrationSerializer,
	ClerkCreateResponseSerializer,
	ClerkCreateSerializer,
	DetailMessageSerializer,
	InvitationEmailLookupSerializer,
	InvitationSerializer,
	InviteEmailSerializer,
	LoginRequestSerializer,
	TokenPairSerializer,
	UserSerializer,
)


def token_pair(user):
	refresh = RefreshToken.for_user(user)
	return {
		"access_token": str(refresh.access_token),
		"refresh_token": str(refresh),
		"user": UserSerializer(user).data,
	}


@extend_schema(tags=["Accounts"])
class HealthCheckView(APIView):
	"""
	Health check endpoint for the accounts service.
	"""
	permission_classes = [AllowAny]

	@extend_schema(responses={200: dict})
	def get(self, request):
		"""
		Returns the health status of the application.
		"""
		return Response(
			{
				"status": "healthy",
				"service": "accounts",
				"message": "Accounts service is running"
			},
			status=status.HTTP_200_OK
		)


@extend_schema(tags=["Accounts"])
class LoginView(APIView):
	permission_classes = [AllowAny]

	@extend_schema(
		request=LoginRequestSerializer,
		responses={200: TokenPairSerializer, 401: DetailMessageSerializer, 403: DetailMessageSerializer},
	)
	def post(self, request):
		email = request.data.get("email", "").strip().lower()
		try:
			candidate = User.objects.get(email__iexact=email)
		except User.DoesNotExist:
			candidate = None
		if candidate is not None and not candidate.is_active:
			return Response({"detail": "This account has been deactivated. Contact your administrator."}, status.HTTP_403_FORBIDDEN)
		user = authenticate(request, email=email, password=request.data.get("password", ""))
		if user is None:
			return Response({"detail": "Unable to log in with those credentials."}, status.HTTP_401_UNAUTHORIZED)
		return Response(token_pair(user))


@extend_schema(tags=["Accounts"])
class LogoutView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(request=None, responses={204: None})
	def post(self, request):
		return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Accounts"])
class MeView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(responses={200: UserSerializer})
	def get(self, request):
		return Response(UserSerializer(request.user).data)


@extend_schema(tags=["Accounts"])
class InvitationsView(APIView):
	permission_classes = [IsMerchant]

	@extend_schema(responses={200: InvitationSerializer(many=True)})
	def get(self, request):
		invitations = Invitation.objects.filter(store=request.user.store).order_by("-created_at")
		for invitation in invitations:
			invitation.refresh_status()
		return Response(InvitationSerializer(invitations, many=True).data)

	@extend_schema(
		request=InviteEmailSerializer,
		responses={201: InvitationSerializer, 400: DetailMessageSerializer},
	)
	def post(self, request):
		email = request.data.get("email", "").strip().lower()
		if not email:
			return Response({"detail": "Email is required."}, status.HTTP_400_BAD_REQUEST)
		if User.objects.filter(email__iexact=email).exists():
			return Response({"detail": "This email already belongs to an account."}, status.HTTP_400_BAD_REQUEST)
		if Invitation.objects.filter(store=request.user.store, email__iexact=email, status=Invitation.Status.PENDING).exists():
			return Response({"detail": "A pending invitation already exists for this email."}, status.HTTP_400_BAD_REQUEST)
		invitation = Invitation.objects.create(
			email=email,
			token=secrets.token_urlsafe(32),
			invited_by=request.user,
			store=request.user.store,
			expires_at=timezone.now() + timedelta(hours=48),
		)
		return Response(InvitationSerializer(invitation).data, status.HTTP_201_CREATED)


@extend_schema(tags=["Accounts"])
class InvitationDetailView(APIView):
	permission_classes = [AllowAny]

	@extend_schema(
		responses={200: InvitationEmailLookupSerializer, 400: DetailMessageSerializer, 404: DetailMessageSerializer},
	)
	def get(self, request, token):
		try:
			invitation = Invitation.objects.get(token=token)
		except Invitation.DoesNotExist:
			return Response({"detail": "This invitation link is invalid."}, status.HTTP_404_NOT_FOUND)
		invitation.refresh_status()
		if invitation.status == Invitation.Status.USED:
			return Response({"detail": "This invitation has already been used."}, status.HTTP_400_BAD_REQUEST)
		if invitation.status == Invitation.Status.EXPIRED:
			return Response({"detail": "This invitation has expired. Ask the merchant to send a new one."}, status.HTTP_400_BAD_REQUEST)
		return Response({"email": invitation.email})


@extend_schema(tags=["Accounts"])
class AdminRegistrationView(APIView):
	permission_classes = [AllowAny]

	@extend_schema(
		request=AdminRegistrationSerializer,
		responses={201: UserSerializer, 400: OpenApiResponse(description="Validation error")},
	)
	@transaction.atomic
	def post(self, request):
		serializer = AdminRegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		invitation = Invitation.objects.select_for_update().get(pk=serializer.validated_data["invitation"].pk)
		invitation.refresh_status()
		if invitation.status != Invitation.Status.PENDING:
			return Response({"detail": "This invitation is no longer valid."}, status.HTTP_400_BAD_REQUEST)
		user = serializer.save()
		return Response(UserSerializer(user).data, status.HTTP_201_CREATED)


@extend_schema(tags=["Accounts"])
class AdminsView(APIView):
	permission_classes = [IsMerchant]

	@extend_schema(responses={200: UserSerializer(many=True)})
	def get(self, request):
		users = User.objects.filter(store=request.user.store, role=User.Role.ADMIN).order_by("name")
		return Response(UserSerializer(users, many=True).data)


@extend_schema(tags=["Accounts"])
class ClerksView(APIView):
	permission_classes = [IsStoreAdmin]

	@extend_schema(responses={200: UserSerializer(many=True)})
	def get(self, request):
		users = User.objects.filter(store=request.user.store, role=User.Role.CLERK).order_by("name")
		return Response(UserSerializer(users, many=True).data)

	@extend_schema(
		request=ClerkCreateSerializer,
		responses={201: ClerkCreateResponseSerializer, 400: DetailMessageSerializer},
	)
	def post(self, request):
		name = request.data.get("name", "").strip()
		email = request.data.get("email", "").strip().lower()
		if len(name) < 2:
			return Response({"detail": "Please enter the clerk's full name."}, status.HTTP_400_BAD_REQUEST)
		if User.objects.filter(email__iexact=email).exists():
			return Response({"detail": "This email already belongs to an account."}, status.HTTP_400_BAD_REQUEST)
		temporary_password = secrets.token_urlsafe(8)
		user = User.objects.create_user(
			email=email,
			password=temporary_password,
			name=name,
			role=User.Role.CLERK,
			store=request.user.store,
		)
		return Response({"user": UserSerializer(user).data, "temporaryPassword": temporary_password}, status.HTTP_201_CREATED)


@extend_schema(tags=["Accounts"])
class UserActionView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(request=None, responses={200: UserSerializer, 400: DetailMessageSerializer, 403: DetailMessageSerializer, 404: DetailMessageSerializer})
	def patch(self, request, user_id, action):
		role = User.Role.ADMIN if request.user.role == User.Role.MERCHANT else User.Role.CLERK
		if (role == User.Role.ADMIN and not IsMerchant().has_permission(request, self)) or (role == User.Role.CLERK and not IsStoreAdmin().has_permission(request, self)):
			return Response({"detail": "You do not have permission to perform this action."}, status.HTTP_403_FORBIDDEN)
		if action not in ("activate", "deactivate"):
			return Response({"detail": "Unknown action."}, status.HTTP_400_BAD_REQUEST)
		try:
			user = User.objects.get(id=user_id, store=request.user.store, role=role)
		except User.DoesNotExist:
			return Response({"detail": "User not found."}, status.HTTP_404_NOT_FOUND)
		user.is_active = action == "activate"
		user.save(update_fields=["is_active"])
		return Response(UserSerializer(user).data)

	@extend_schema(request=None, responses={204: None, 403: DetailMessageSerializer, 404: DetailMessageSerializer})
	def delete(self, request, user_id, action):
		role = User.Role.ADMIN if request.user.role == User.Role.MERCHANT else User.Role.CLERK
		allowed = (role == User.Role.ADMIN and request.user.role == User.Role.MERCHANT) or (role == User.Role.CLERK and request.user.role == User.Role.ADMIN)
		if not allowed:
			return Response({"detail": "You do not have permission to perform this action."}, status.HTTP_403_FORBIDDEN)
		deleted, _ = User.objects.filter(id=user_id, store=request.user.store, role=role).delete()
		if not deleted:
			return Response({"detail": "User not found."}, status.HTTP_404_NOT_FOUND)
		return Response(status=status.HTTP_204_NO_CONTENT)
