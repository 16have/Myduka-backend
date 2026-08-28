from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .serializers import MerchantRegistrationSerializer


class MerchantRegistrationView(generics.GenericAPIView):
    serializer_class = MerchantRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # public — this IS the signup endpoint

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "user": {
                    "id": result["user"].id,
                    "username": result["user"].username,
                    "email": result["user"].email,
                    "role": result["user"].role,
                },
                "store": {
                    "id": result["store"].id,
                    "name": result["store"].name,
                },
            },
            status=status.HTTP_201_CREATED,
        )