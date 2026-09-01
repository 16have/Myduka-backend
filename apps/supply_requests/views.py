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
        return SupplyRequest.objects.filter(product__store_id__in=member_store_ids)

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        is_member = StoreMembership.objects.filter(
            user=self.request.user, store=product.store
        ).exists()
        if not is_member:
            raise PermissionDenied("You are not a member of this product's store.")
        serializer.save(requested_by=self.request.user, status=SupplyRequest.Status.PENDING)

    def perform_update(self, serializer):
        supply_request = self.get_object()
        membership = StoreMembership.objects.filter(
            user=self.request.user, store=supply_request.product.store
        ).first()
        if not membership or membership.role not in ("owner", "admin"):
            raise PermissionDenied("Only store admins/owners can update supply requests.")

        old_status = supply_request.status
        new_status = serializer.validated_data.get("status", old_status)

        # If the status is being moved into a decided/received state and quantity increases stock,
        # only adjust stock the moment it actually transitions INTO "Received" for the first time.
        instance = serializer.save(reviewed_by=self.request.user)

        if old_status != SupplyRequest.Status.RECEIVED and new_status == SupplyRequest.Status.RECEIVED:
            product = instance.product
            product.quantity += instance.quantity_requested
            product.save()