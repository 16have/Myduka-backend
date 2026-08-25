from django.contrib import admin

from .models import Product, SpoilageRecord, StockTransaction, SupplyRequest

admin.site.register(Product)
admin.site.register(StockTransaction)
admin.site.register(SpoilageRecord)
admin.site.register(SupplyRequest)
