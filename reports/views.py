from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    ClerkPerformanceReportSerializer,
    InventoryReportSerializer,
    ProductPerformanceReportSerializer,
    ReportErrorSerializer,
    StorePerformanceReportSerializer,
)
from .services.report_services import ReportService

PERIOD_PARAMETER = OpenApiParameter(
    name="period",
    description="Reporting window: 'weekly' (default), 'monthly', or 'annual'.",
    required=False,
    type=str,
)


@extend_schema(tags=["Reports"])
class InventoryReportView(APIView):
    """
    Inventory report: current stock levels and received/spoiled movement.

    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[PERIOD_PARAMETER],
        responses={200: InventoryReportSerializer, 400: ReportErrorSerializer},
    )
    def get(self, request):
        period = request.query_params.get("period", "weekly")
        try:
            report = ReportService.inventory_report(period, store=request.user.store)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Reports"])
class ProductPerformanceView(APIView):
    """
    Product performance report: sales metrics by product.

    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[PERIOD_PARAMETER],
        responses={200: ProductPerformanceReportSerializer, 400: ReportErrorSerializer},
    )
    def get(self, request):
        period = request.query_params.get("period", "weekly")
        try:
            report = ReportService.product_performance(period, store=request.user.store)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Reports"])
class StorePerformanceView(APIView):
    """
    Store performance report: sales metrics for the caller's store.

    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[PERIOD_PARAMETER],
        responses={200: StorePerformanceReportSerializer, 400: ReportErrorSerializer},
    )
    def get(self, request):
        period = request.query_params.get("period", "weekly")
        try:
            report = ReportService.store_performance(period, store=request.user.store)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Reports"])
class ClerkPerformanceView(APIView):
    """
    Clerk performance report: sales metrics by clerk.

    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[PERIOD_PARAMETER],
        responses={200: ClerkPerformanceReportSerializer, 400: ReportErrorSerializer},
    )
    def get(self, request):
        period = request.query_params.get("period", "weekly")
        try:
            report = ReportService.clerk_performance(period, store=request.user.store)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
