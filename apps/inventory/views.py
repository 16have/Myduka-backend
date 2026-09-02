from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Product
from .serializers import ProductSerializer
from apps.accounts.models import StoreMembership
from .models import StockReceipt, SpoilageRecord
from .serializers import StockReceiptSerializer, SpoilageRecordSerializer
from rest_framework.exceptions import PermissionDenied


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return products from stores the user is a member of
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        return Product.objects.filter(store_id__in=member_store_ids)

    def perform_create(self, serializer):
        store = serializer.validated_data["store"]
        is_member = StoreMembership.objects.filter(
            user=self.request.user, store=store
        ).exists()
        if not is_member:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not a member of this store.")
        serializer.save()

class StockReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = StockReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        qs = StockReceipt.objects.filter(product__store_id__in=member_store_ids)

        payment_status = self.request.query_params.get("payment_status")
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        return qs

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        is_member = StoreMembership.objects.filter(
            user=self.request.user, store=product.store
        ).exists()
        if not is_member:
            raise PermissionDenied("You are not a member of this store.")

        receipt = serializer.save(received_by=self.request.user)
        product.quantity += receipt.quantity_received
        product.save()


class SpoilageRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SpoilageRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        return SpoilageRecord.objects.filter(product__store_id__in=member_store_ids)

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        is_member = StoreMembership.objects.filter(
            user=self.request.user, store=product.store
        ).exists()
        if not is_member:
            raise PermissionDenied("You are not a member of this store.")

        quantity_spoiled = serializer.validated_data["quantity_spoiled"]
        if quantity_spoiled > product.quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot spoil more stock than currently in inventory.")

        serializer.save(recorded_by=self.request.user)
        product.quantity -= quantity_spoiled
        product.save()