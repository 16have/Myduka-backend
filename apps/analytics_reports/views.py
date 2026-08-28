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