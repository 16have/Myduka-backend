from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class HealthCheckView(APIView):
    """
    Health check endpoint for the accounts service.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Returns the health status of the application.
        """
        return Response(
            {
                "status": "healthy",
                "service": "accounts",
                "message": "Accounts service is running"
            },
            status=status.HTTP_200_OK
        )
