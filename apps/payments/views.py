from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions, status as http_status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
import uuid
from .models import Payment
from .serializers import PaymentSerializer
from apps.accounts.models import StoreMembership


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        return Payment.objects.filter(
            supply_request__product__store_id__in=member_store_ids
        )

    def perform_create(self, serializer):
        supply_request = serializer.validated_data["supply_request"]
        is_member = StoreMembership.objects.filter(
            user=self.request.user, store=supply_request.product.store
        ).exists()
        if not is_member:
            raise PermissionDenied("You are not a member of this store.")

        # MOCK: simulate an STK push initiation.
        # Real Daraja integration will replace this block with an actual API call.
        payment = serializer.save(
            checkout_request_id=f"mock-checkout-{uuid.uuid4().hex[:10]}",
            merchant_request_id=f"mock-merchant-{uuid.uuid4().hex[:10]}",
            status=Payment.Status.PENDING,
        )
        return payment

    @action(detail=True, methods=["post"])
    def simulate_success(self, request, pk=None):
        """MOCK ONLY — simulates Safaricom's callback confirming payment.
        Remove or replace with the real /callback/ endpoint once Daraja is wired in."""
        payment = self.get_object()
        payment.status = Payment.Status.SUCCESS
        payment.mpesa_receipt_number = f"MOCK{uuid.uuid4().hex[:8].upper()}"
        payment.save()
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def simulate_failure(self, request, pk=None):
        """MOCK ONLY — simulates a failed payment callback."""
        payment = self.get_object()
        payment.status = Payment.Status.FAILED
        payment.save()
        return Response(PaymentSerializer(payment).data)