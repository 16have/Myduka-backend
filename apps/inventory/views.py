import uuid
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Product, StockReceipt, SpoilageRecord
from .serializers import ProductSerializer, StockReceiptSerializer, SpoilageRecordSerializer
from apps.accounts.models import StoreMembership


def _store_ids(user):
    return StoreMembership.objects.filter(user=user).values_list("store_id", flat=True)


def _assert_member(user, store):
    if not StoreMembership.objects.filter(user=user, store=store).exists():
        raise PermissionDenied("You are not a member of this store.")


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(store_id__in=_store_ids(self.request.user))

    def perform_create(self, serializer):
        store = serializer.validated_data["store"]
        _assert_member(self.request.user, store)
        serializer.save()


class StockReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = StockReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StockReceipt.objects.filter(
            product__store_id__in=_store_ids(self.request.user)
        ).select_related("product", "received_by")
        ps = self.request.query_params.get("payment_status")
        if ps:
            # accept both "Paid"/"unpaid" etc.
            ps_map = {"Paid": "paid", "Not Paid": "unpaid", "paid": "paid", "unpaid": "unpaid"}
            qs = qs.filter(payment_status=ps_map.get(ps, ps))
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        product = serializer.validated_data["product_id"]
        _assert_member(self.request.user, product.store)

        qty = serializer.validated_data["quantity_received"]
        cost = serializer.validated_data["unit_cost"]

        selling_price = serializer.validated_data.get("selling_price")

        ref = "REC-" + uuid.uuid4().hex[:8].upper()
        serializer.save(received_by=self.request.user, reference_number=ref)

        product.quantity += qty
        product.buying_price = cost
        if selling_price is not None:
            product.selling_price = selling_price
        product.save()

    def perform_update(self, serializer):
        """Allow admin to mark payment_status paid/unpaid."""
        instance = self.get_object()
        _assert_member(self.request.user, instance.product.store)
        serializer.save()


class SpoilageRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SpoilageRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SpoilageRecord.objects.filter(
            product__store_id__in=_store_ids(self.request.user)
        ).select_related("product", "recorded_by").order_by("-created_at")

    def perform_create(self, serializer):
        product = serializer.validated_data["product_id"]
        _assert_member(self.request.user, product.store)

        qty = serializer.validated_data["quantity_spoiled"]
        if qty > product.quantity:
            raise ValidationError(
                {"quantity": f"Only {product.quantity} unit(s) available — cannot spoil {qty}."}
            )

        serializer.save(recorded_by=self.request.user)
        product.quantity -= qty
        product.save()
