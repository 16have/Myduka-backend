from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "supply_request", "amount", "phone_number", "status",
            "mpesa_receipt_number", "checkout_request_id", "merchant_request_id",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "mpesa_receipt_number",
            "checkout_request_id", "merchant_request_id",
            "created_at", "updated_at",
        ]