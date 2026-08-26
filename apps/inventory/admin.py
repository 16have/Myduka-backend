from django.contrib import admin
from .models import Store, Product, Clerk, Transaction


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'created_at']
    search_fields = ['name', 'location']
    ordering = ['-created_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'quantity_in_stock', 'created_at']
    search_fields = ['name', 'sku']
    list_filter = ['created_at']
    ordering = ['-created_at']


@admin.register(Clerk)
class ClerkAdmin(admin.ModelAdmin):
    list_display = ['user', 'store', 'employee_id', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id']
    list_filter = ['store', 'created_at']
    ordering = ['-created_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'clerk', 'store', 'transaction_type', 'quantity', 'amount', 'created_at']
    search_fields = ['product__name', 'clerk__user__first_name', 'store__name']
    list_filter = ['transaction_type', 'store', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

from .models import Product, Inventory, StockTransaction, SpoilageRecord, SupplyRequest

admin.site.register(Product)
admin.site.register(Inventory)
admin.site.register(StockTransaction)
admin.site.register(SpoilageRecord)
admin.site.register(SupplyRequest)
