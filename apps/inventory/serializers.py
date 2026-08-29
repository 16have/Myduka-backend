from rest_framework import serializers
from .models import Product
from .models import StockReceipt, SpoilageRecord


class ProductSerializer(serializers.ModelSerializer):
    stock_status = serializers.ReadOnlyField()
    margin = serializers.ReadOnlyField()
    current_stock = serializers.IntegerField(source="quantity", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "store", "name", "sku", "category",
            "buying_price", "selling_price", "quantity", "current_stock",
            "low_stock_threshold", "stock_status", "margin",
            "supplier_name", "supplier_contact", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        
class StockReceiptSerializer(serializers.ModelSerializer):
    total_cost = serializers.ReadOnlyField()

    class Meta:
        model = StockReceipt
        fields = [
            "id", "product", "quantity_received", "unit_cost", "total_cost",
            "supplier_name", "received_by", "payment_status", "created_at",
        ]
        read_only_fields = ["id", "received_by", "created_at"]


class SpoilageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpoilageRecord
        fields = ["id", "product", "quantity_spoiled", "reason", "recorded_by", "created_at"]
        read_only_fields = ["id", "recorded_by", "created_at"]