from django.urls import path

urlpatterns = []
from django.urls import path
from .views import MerchantRegistrationView

urlpatterns = [
    path("register/", MerchantRegistrationView.as_view(), name="merchant-register"),
]