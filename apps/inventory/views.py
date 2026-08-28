from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Product
from .serializers import ProductSerializer
from apps.accounts.models import StoreMembership


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