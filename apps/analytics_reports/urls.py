from django.urls import path
from .views import LowStockReportView, StockSummaryReportView, DashboardSummaryReportView

urlpatterns = [
    path("reports/low-stock/", LowStockReportView.as_view(), name="low-stock-report"),
    path("reports/stock-summary/", StockSummaryReportView.as_view(), name="stock-summary-report"),
    path("reports/dashboard-summary/", DashboardSummaryReportView.as_view(), name="dashboard-summary-report"),
]