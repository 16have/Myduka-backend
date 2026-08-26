from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class APIRootView(APIView):
    """
    Root API endpoint that displays all available endpoints.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Returns information about available API endpoints.
        """
        return Response(
            {
                "status": "success",
                "message": "MyDuka Backend API",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/accounts/health/",
                    "reports": {
                        "inventory": "/api/v1/reports/inventory/",
                        "products": "/api/v1/reports/products/",
                        "stores": "/api/v1/reports/stores/",
                        "clerks": "/api/v1/reports/clerks/",
                    },
                    "documentation": "/admin/",
                },
                "query_parameters": {
                    "reports": {
                        "period": "weekly | monthly | annual (default: weekly)"
                    }
                }
            },
            status=status.HTTP_200_OK
        )
