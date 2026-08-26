from decimal import Decimal

from rest_framework import serializers

from .models import Inventory, Product, SpoilageRecord, StockTransaction, SupplyRequest


class ProductSerializer(serializers.ModelSerializer):
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "category",
            "buying_price",
            "selling_price",
            "current_stock",
            "minimum_stock_level",
            "stock_status",
            "created_at",
            "updated_at",
        ]


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = [
            "id",
            "product_id",
            "quantity",
            "current_stock",
            "created_at",
            "updated_at",
        ]


class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    clerk_name = serializers.CharField(source="clerk.get_full_name", read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = StockTransaction
        fields = [
            "id",
            "product_id",
            "product_name",
            "clerk",
            "clerk_name",
            "transaction_type",
            "quantity",
            "buying_price",
            "selling_price",
            "total_amount",
            "payment_status",
            "supplier",
            "reference_number",
            "notes",
            "created_at",
        ]

    def get_total_amount(self, obj):
        if obj.buying_price is not None:
            return float(obj.buying_price) * obj.quantity
        return None


class SpoilageRecordSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    recorded_by_name = serializers.CharField(source="recorder.get_full_name", read_only=True)

    class Meta:
        model = SpoilageRecord
        fields = [
            "id",
            "product_id",
            "product_name",
            "quantity",
            "reason",
            "notes",
            "recorded_by",
            "recorded_by_name",
            "created_at",
        ]


class SupplyRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    requested_by_name = serializers.CharField(source="requester.get_full_name", read_only=True)

    class Meta:
        model = SupplyRequest
        fields = [
            "id",
            "product_id",
            "product_name",
            "requested_by",
            "requested_by_name",
            "quantity",
            "reason",
            "notes",
            "status",
            "admin_response",
            "created_at",
            "updated_at",
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__("apps.accounts.models", fromlist=["User"]).User
        fields = ["id", "name", "role"]
