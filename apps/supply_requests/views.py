from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import SupplyRequest
from .serializers import SupplyRequestSerializer
from apps.accounts.models import StoreMembership


class SupplyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = SupplyRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        return SupplyRequest.objects.filter(
            product__store_id__in=member_store_ids
        ).select_related("product", "requested_by", "reviewed_by").order_by("-created_at")

    def perform_create(self, serializer):
        product = serializer.validated_data["product_id"]  # still product_id before create()
        if not StoreMembership.objects.filter(user=self.request.user, store=product.store).exists():
            raise PermissionDenied("You are not a member of this product's store.")
        serializer.save(requested_by=self.request.user, status=SupplyRequest.Status.PENDING)

    def perform_update(self, serializer):
        # serializer.instance is the object already fetched by get_object() in the view
        instance = serializer.instance
        membership = StoreMembership.objects.filter(
            user=self.request.user, store=instance.product.store
        ).first()
        if not membership or membership.role not in ("owner", "admin"):
            raise PermissionDenied("Only store admins/owners can update supply requests.")

        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)

        updated = serializer.save(reviewed_by=self.request.user)

        # Auto-increment stock when status transitions to Received for the first time
        if old_status != SupplyRequest.Status.RECEIVED and new_status == SupplyRequest.Status.RECEIVED:
            product = updated.product
            product.quantity += updated.quantity_requested
            product.save()
