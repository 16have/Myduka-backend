from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions, status as http_status
from rest_framework.decorators import action
from rest_framework.response import Response
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
        serializer.save(requested_by=self.request.user)

    def _check_admin_or_owner(self, request, supply_request):
        membership = StoreMembership.objects.filter(
            user=request.user, store=supply_request.product.store
        ).first()
        if not membership or membership.role not in ("owner", "admin"):
            raise PermissionDenied("Only store admins/owners can review supply requests.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        supply_request = self.get_object()
        self._check_admin_or_owner(request, supply_request)
        supply_request.status = SupplyRequest.Status.APPROVED
        supply_request.reviewed_by = request.user
        supply_request.save()
        return Response(SupplyRequestSerializer(supply_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        supply_request = self.get_object()
        self._check_admin_or_owner(request, supply_request)
        supply_request.status = SupplyRequest.Status.REJECTED
        supply_request.reviewed_by = request.user
        supply_request.save()
        return Response(SupplyRequestSerializer(supply_request).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        supply_request = self.get_object()
        self._check_admin_or_owner(request, supply_request)
        if supply_request.status != SupplyRequest.Status.APPROVED:
            return Response(
                {"detail": "Only approved requests can be fulfilled."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        supply_request.status = SupplyRequest.Status.FULFILLED
        supply_request.product.quantity += supply_request.quantity_requested
        supply_request.product.save()
        supply_request.save()
        return Response(SupplyRequestSerializer(supply_request).data)