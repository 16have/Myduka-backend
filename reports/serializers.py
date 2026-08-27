from rest_framework import serializers


class ReportErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class InventoryReportItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    current_stock = serializers.IntegerField()
    received_qty = serializers.IntegerField()
    sold_qty = serializers.IntegerField()
    spoiled_qty = serializers.IntegerField()
    selling_price = serializers.CharField()


class InventoryReportSerializer(serializers.Serializer):
    report = serializers.CharField()
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_products = serializers.IntegerField()
    data = InventoryReportItemSerializer(many=True)


class ProductPerformanceItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.CharField()
    transaction_count = serializers.IntegerField()
    avg_transaction_value = serializers.CharField()


class ProductPerformanceReportSerializer(serializers.Serializer):
    report = serializers.CharField()
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_products = serializers.IntegerField()
    data = ProductPerformanceItemSerializer(many=True)


class StorePerformanceItemSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    store_name = serializers.CharField()
    total_sales = serializers.CharField()
    total_transactions = serializers.IntegerField()
    avg_transaction_value = serializers.CharField()
    active_clerks = serializers.IntegerField()


class StorePerformanceReportSerializer(serializers.Serializer):
    report = serializers.CharField()
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_stores = serializers.IntegerField()
    data = StorePerformanceItemSerializer(many=True)


class ClerkPerformanceItemSerializer(serializers.Serializer):
    clerk_id = serializers.IntegerField()
    clerk_name = serializers.CharField()
    total_sales = serializers.CharField()
    total_transactions = serializers.IntegerField()
    avg_transaction_value = serializers.CharField()


class ClerkPerformanceReportSerializer(serializers.Serializer):
    report = serializers.CharField()
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_clerks = serializers.IntegerField()
    data = ClerkPerformanceItemSerializer(many=True)
