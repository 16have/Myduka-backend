from django.urls import path

from .views import (
    InventoryStatsAPIView,
    PaymentStatusUpdateAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
    ReceivedStockListAPIView,
    ReceiveStockAPIView,
    SellStockAPIView,
    SpoilageListCreateAPIView,
    SupplyRequestListCreateAPIView,
    SupplyRequestUpdateAPIView,
    UnpaidPaymentsListAPIView,
)

urlpatterns = [
    path("inventory", ProductListAPIView.as_view(), name="list-inventory"),
    path("inventory/<int:product_id>", ProductDetailAPIView.as_view(), name="get-inventory-item"),
    path("inventory/stats", InventoryStatsAPIView.as_view(), name="inventory-stats"),
    path("stock/receive", ReceiveStockAPIView.as_view(), name="receive-stock"),
    path("stock/received", ReceivedStockListAPIView.as_view(), name="list-received-stock"),
    path("stock/sell", SellStockAPIView.as_view(), name="sell-stock"),
    path("spoilage", SpoilageListCreateAPIView.as_view(), name="spoilage-list-create"),
    path("supply-requests", SupplyRequestListCreateAPIView.as_view(), name="supply-requests-list-create"),
    path("supply-requests/<int:request_id>", SupplyRequestUpdateAPIView.as_view(), name="supply-request-update"),
    path("payments/unpaid", UnpaidPaymentsListAPIView.as_view(), name="list-unpaid-payments"),
    path("payments/<int:transaction_id>/status", PaymentStatusUpdateAPIView.as_view(), name="update-payment-status"),
]
