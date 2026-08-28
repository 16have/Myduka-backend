from django.urls import path
from .views import LowStockReportView, StockSummaryReportView

urlpatterns = [
    path("reports/low-stock/", LowStockReportView.as_view(), name="low-stock-report"),
    path("reports/stock-summary/", StockSummaryReportView.as_view(), name="stock-summary-report"),
]