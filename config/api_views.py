from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


@extend_schema(tags=["Root"])
class APIRootView(APIView):
    """
    Root API endpoint that displays all available endpoints.
    """
    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(
            {
                "status": "success",
                "message": "MyDuka Backend API",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/auth/health/",
                    "docs": "/api/docs/",
                    "schema": "/api/schema/",
                    "accounts": {
                        "login": "/api/auth/login",
                        "logout": "/api/auth/logout",
                        "me": "/api/auth/me",
                        "invitations": "/api/auth/invitations",
                        "register_admin": "/api/auth/register-admin",
                        "admins": "/api/auth/admins",
                        "clerks": "/api/auth/clerks",
                    },
                    "inventory": {
                        "products": "/api/inventory",
                        "product_detail": "/api/inventory/<id>",
                        "stats": "/api/inventory/stats",
                        "receive_stock": "/api/stock/receive",
                        "received_stock": "/api/stock/received",
                        "sell_stock": "/api/stock/sell",
                        "spoilage": "/api/spoilage",
                        "supply_requests": "/api/supply-requests",
                        "unpaid_payments": "/api/payments/unpaid",
                    },
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
