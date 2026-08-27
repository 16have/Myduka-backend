from rest_framework import serializers

from .models import Inventory, Product, SpoilageRecord, StockTransaction, SupplyRequest


class ProductSerializer(serializers.ModelSerializer):
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
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
        read_only_fields = ["store"]


class InventorySerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)

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
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    clerk_name = serializers.CharField(source="clerk.name", read_only=True)
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

    def get_total_amount(self, obj) -> float | None:
        price = obj.selling_price if obj.transaction_type == StockTransaction.TransactionType.SOLD else obj.buying_price
        if price is not None:
            return float(price) * obj.quantity
        return None


class SpoilageRecordSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    recorder_name = serializers.CharField(source="recorder.name", read_only=True)

    class Meta:
        model = SpoilageRecord
        fields = [
            "id",
            "product_id",
            "product_name",
            "quantity",
            "reason",
            "notes",
            "recorder",
            "recorder_name",
            "created_at",
        ]


class SupplyRequestSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    requester_name = serializers.CharField(source="requester.name", read_only=True)

    class Meta:
        model = SupplyRequest
        fields = [
            "id",
            "product_id",
            "product_name",
            "requester",
            "requester_name",
            "quantity",
            "reason",
            "notes",
            "status",
            "admin_response",
            "created_at",
            "updated_at",
        ]


class ErrorSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()


class InventoryStatsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_stock = serializers.IntegerField()
    low_stock = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    unpaid_stock = serializers.IntegerField()
    pending_supply_requests = serializers.IntegerField()


class ProductCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    buying_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    minimum_stock_level = serializers.IntegerField(required=False, default=0)


class ReceiveStockRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    buying_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_status = serializers.ChoiceField(choices=["Paid", "Not Paid"])
    supplier = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class SellStockRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    payment_status = serializers.ChoiceField(choices=["Paid", "Not Paid"], required=False, default="Paid")
    notes = serializers.CharField(required=False, allow_blank=True)


class StockTransactionResultSerializer(StockTransactionSerializer):
    new_stock_level = serializers.IntegerField()

    class Meta(StockTransactionSerializer.Meta):
        fields = StockTransactionSerializer.Meta.fields + ["new_stock_level"]


class SpoilageRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=["Broken", "Expired", "Other"])
    notes = serializers.CharField(required=False, allow_blank=True)


class SpoilageRecordResultSerializer(SpoilageRecordSerializer):
    new_stock_level = serializers.IntegerField()

    class Meta(SpoilageRecordSerializer.Meta):
        fields = SpoilageRecordSerializer.Meta.fields + ["new_stock_level"]


class SupplyRequestCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)


class SupplyRequestDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["Approved", "Declined"])
    admin_response = serializers.CharField(required=False, allow_blank=True)


class PaymentStatusUpdateRequestSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=["Paid", "Not Paid"])
