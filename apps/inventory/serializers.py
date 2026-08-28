from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "store", "name", "sku", "price", "quantity",
            "supplier_name", "supplier_contact", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]