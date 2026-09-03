from rest_framework import viewsets, permissions
from .models import Store
from .serializers import StoreSerializer
from apps.accounts.models import StoreMembership
from drf_spectacular.utils import extend_schema_view, extend_schema


@extend_schema_view(
    list=extend_schema(summary="List your stores", tags=["Stores"]),
    create=extend_schema(summary="Create a new store", tags=["Stores"]),
)
class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_store_ids = StoreMembership.objects.filter(
            user=self.request.user
        ).values_list("store_id", flat=True)
        return Store.objects.filter(id__in=member_store_ids)

    def perform_create(self, serializer):
        store = serializer.save()
        StoreMembership.objects.create(
            user=self.request.user,
            store=store,
            role=StoreMembership.Role.OWNER,
            is_primary=False,
        )
