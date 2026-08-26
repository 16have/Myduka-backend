from django.contrib import admin

from .models import Product, Inventory, StockTransaction, SpoilageRecord, SupplyRequest

admin.site.register(Product)
admin.site.register(Inventory)
admin.site.register(StockTransaction)
admin.site.register(SpoilageRecord)
admin.site.register(SupplyRequest)
