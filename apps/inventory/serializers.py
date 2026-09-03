from rest_framework import serializers
from .models import Product, StockReceipt, SpoilageRecord


class ProductSerializer(serializers.ModelSerializer):
    stock_status = serializers.ReadOnlyField()
    margin = serializers.ReadOnlyField()
    current_stock = serializers.IntegerField(source="quantity", read_only=True)
    minimum_stock_level = serializers.IntegerField(source="low_stock_threshold", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "store", "name", "sku", "category",
            "buying_price", "selling_price", "quantity", "current_stock",
            "low_stock_threshold", "minimum_stock_level", "stock_status", "margin",
            "supplier_name", "supplier_contact", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Payment status normaliser shared by create and update
# ---------------------------------------------------------------------------
_PS_MAP = {"Paid": "paid", "Not Paid": "unpaid", "paid": "paid", "unpaid": "unpaid"}


class StockReceiptSerializer(serializers.ModelSerializer):
    # ── read-only output aliases ──────────────────────────────────────────
    total_cost = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField(source="total_cost")
    product_name = serializers.CharField(source="product.name", read_only=True)
    clerk_name = serializers.CharField(source="received_by.username", read_only=True)
    # "quantity" and "buying_price" are read aliases; the writable model fields
    # are quantity_received / unit_cost — kept separate to avoid DRF conflicts
    quantity = serializers.IntegerField(source="quantity_received", read_only=True)
    buying_price_out = serializers.DecimalField(
        source="unit_cost", max_digits=10, decimal_places=2, read_only=True
    )
    supplier_out = serializers.CharField(source="supplier_name", read_only=True)
    new_stock_level = serializers.SerializerMethodField()

    def get_new_stock_level(self, obj):
        return obj.product.quantity

    # ── writable fields (frontend names) ─────────────────────────────────
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, required=True
    )
    quantity_received = serializers.IntegerField(write_only=True, min_value=1)
    unit_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, write_only=True, min_value=0
    )
    supplier_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    payment_status = serializers.ChoiceField(
        choices=list(_PS_MAP.keys()), required=True
    )

    def validate_payment_status(self, value):
        return _PS_MAP[value]

    class Meta:
        model = StockReceipt
        fields = [
            # identifiers / read
            "id", "product_name", "clerk_name",
            "quantity", "buying_price_out", "supplier_out",
            "selling_price", "total_cost", "total_amount",
            "payment_status", "reference_number", "notes", "date_received",
            "new_stock_level", "created_at",
            # write-only
            "product_id", "quantity_received", "unit_cost", "supplier_name",
        ]
        read_only_fields = ["id", "reference_number", "created_at"]

    def to_representation(self, instance):
        """Expose buying_price and supplier under the names the frontend expects."""
        data = super().to_representation(instance)
        data["buying_price"] = data.pop("buying_price_out", None)
        data["supplier"] = data.pop("supplier_out", None)
        return data

    def create(self, validated_data):
        product = validated_data.pop("product_id")
        validated_data["product"] = product
        return super().create(validated_data)


class SpoilageRecordSerializer(serializers.ModelSerializer):
    # ── read-only output ──────────────────────────────────────────────────
    product_name = serializers.CharField(source="product.name", read_only=True)
    clerk_name = serializers.CharField(source="recorded_by.username", read_only=True)
    quantity = serializers.IntegerField(source="quantity_spoiled", read_only=True)
    new_stock_level = serializers.SerializerMethodField()

    def get_new_stock_level(self, obj):
        return obj.product.quantity

    # ── writable fields ───────────────────────────────────────────────────
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, required=True
    )
    quantity_spoiled = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = SpoilageRecord
        fields = [
            "id", "product_name", "clerk_name",
            "quantity", "quantity_spoiled",
            "reason", "notes", "date",
            "recorded_by", "created_at", "new_stock_level",
            # write-only
            "product_id",
        ]
        read_only_fields = ["id", "recorded_by", "created_at"]

    def create(self, validated_data):
        product = validated_data.pop("product_id")
        validated_data["product"] = product
        return super().create(validated_data)
