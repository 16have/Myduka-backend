from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .services.report_services import ReportService


class InventoryReportView(APIView):
    """
    API view for inventory reports.
    
    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get inventory report.
        """
        period = request.query_params.get("period", "weekly")
        
        try:
            report = ReportService.inventory_report(period)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProductPerformanceView(APIView):
    """
    API view for product performance reports.
    
    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get product performance report showing sales metrics.
        """
        period = request.query_params.get("period", "weekly")
        
        try:
            report = ReportService.product_performance(period)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class StorePerformanceView(APIView):
    """
    API view for store performance reports.
    
    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get store performance report showing sales by store.
        """
        period = request.query_params.get("period", "weekly")
        
        try:
            report = ReportService.store_performance(period)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ClerkPerformanceView(APIView):
    """
    API view for clerk performance reports.
    
    Query Parameters:
        - period: 'weekly', 'monthly', or 'annual' (default: 'weekly')
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get clerk performance report showing individual sales metrics.
        """
        period = request.query_params.get("period", "weekly")
        
        try:
            report = ReportService.clerk_performance(period)
            return Response(report, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
