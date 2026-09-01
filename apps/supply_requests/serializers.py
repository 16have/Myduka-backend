from rest_framework import serializers
from .models import SupplyRequest


class SupplyRequestSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(source="quantity_requested")
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = SupplyRequest
        fields = [
            "id", "product", "product_name", "requested_by", "requested_by_name",
            "reviewed_by", "quantity", "reason", "notes", "admin_response",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "requested_by", "reviewed_by", "created_at", "updated_at"]