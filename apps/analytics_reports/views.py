from django.shortcuts import render

# Create your views here.
from rest_framework import views, permissions
from rest_framework.response import Response
from django.db.models import Sum, F, Count
from apps.inventory.models import Product
from apps.accounts.models import StoreMembership


def _member_store_ids(user):
    return StoreMembership.objects.filter(user=user).values_list("store_id", flat=True)


class LowStockReportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        threshold = int(request.query_params.get("threshold", 10))
        store_ids = _member_store_ids(request.user)

        low_stock = Product.objects.filter(
            store_id__in=store_ids,
            quantity__lte=threshold,
        ).values("id", "name", "sku", "quantity", "store_id", "store__name")

        return Response({
            "threshold": threshold,
            "count": low_stock.count(),
            "products": list(low_stock),
        })


class StockSummaryReportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        store_ids = _member_store_ids(request.user)

        summary = (
            Product.objects.filter(store_id__in=store_ids)
            .values("store_id", "store__name")
            .annotate(
                total_products=Count("id"),
                total_units=Sum("quantity"),
                total_value=Sum(F("quantity") * F("price")),
            )
            .order_by("store__name")
        )

        return Response({"stores": list(summary)})

class DashboardSummaryReportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        store_ids = _member_store_ids(request.user)
        products = Product.objects.filter(store_id__in=store_ids)

        total_products = products.count()
        total_stock = products.aggregate(total=Sum("quantity"))["total"] or 0
        low_stock = sum(1 for p in products if p.stock_status == Product.StockStatus.LOW_STOCK)
        out_of_stock = sum(1 for p in products if p.stock_status == Product.StockStatus.OUT_OF_STOCK)

        from apps.supply_requests.models import SupplyRequest
        pending_supply_requests = SupplyRequest.objects.filter(
            product__store_id__in=store_ids,
            status=SupplyRequest.Status.PENDING,
        ).count()

        return Response({
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "pending_supply_requests": pending_supply_requests,
        })