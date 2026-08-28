from rest_framework import serializers
from .models import SupplyRequest


class SupplyRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyRequest
        fields = [
            "id", "product", "requested_by", "reviewed_by",
            "quantity_requested", "status", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "requested_by", "reviewed_by", "status", "created_at", "updated_at"]