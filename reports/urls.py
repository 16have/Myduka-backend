from django.urls import path

from .views import (
    InventoryReportView,
    ProductPerformanceView,
    StorePerformanceView,
    ClerkPerformanceView,
)

app_name = 'reports'

urlpatterns = [
    path(
        "inventory/",
        InventoryReportView.as_view(),
        name="inventory-report",
    ),
    path(
        "products/",
        ProductPerformanceView.as_view(),
        name="product-performance",
    ),
    path(
        "stores/",
        StorePerformanceView.as_view(),
        name="store-performance",
    ),
    path(
        "clerks/",
        ClerkPerformanceView.as_view(),
        name="clerk-performance",
    ),
]
