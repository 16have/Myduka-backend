from django.urls import path
from .views import MerchantRegistrationView, CreateInviteView, AcceptInviteView

urlpatterns = [
    path("register/", MerchantRegistrationView.as_view(), name="merchant-register"),
    path("invites/", CreateInviteView.as_view(), name="create-invite"),
    path("invites/accept/", AcceptInviteView.as_view(), name="accept-invite"),
]