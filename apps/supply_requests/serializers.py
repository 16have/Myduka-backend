from rest_framework import serializers
from .models import SupplyRequest
from apps.inventory.models import Product


class SupplyRequestSerializer(serializers.ModelSerializer):
    # ── read-only output ──────────────────────────────────────────────────
    product_name = serializers.CharField(source="product.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    quantity = serializers.IntegerField(source="quantity_requested", read_only=True)

    # ── writable fields ───────────────────────────────────────────────────
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, required=False
    )
    quantity_requested = serializers.IntegerField(write_only=True, min_value=1, required=False)

    class Meta:
        model = SupplyRequest
        fields = [
            "id", "product_name", "requested_by_name",
            "requested_by", "reviewed_by",
            "quantity", "quantity_requested",
            "reason", "notes", "admin_response",
            "status", "created_at", "updated_at",
            # write-only
            "product_id",
        ]
        read_only_fields = ["id", "requested_by", "reviewed_by", "created_at", "updated_at"]

    def create(self, validated_data):
        product = validated_data.pop("product_id", None)
        if product is None:
            raise serializers.ValidationError({"product_id": "This field is required."})
        qty = validated_data.pop("quantity_requested", None)
        if qty is None:
            raise serializers.ValidationError({"quantity_requested": "This field is required."})
        validated_data["product"] = product
        validated_data["quantity_requested"] = qty
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # product_id not allowed on update
        validated_data.pop("product_id", None)
        return super().update(instance, validated_data)
