from django.urls import path
from .views import (
    MerchantRegistrationView, CreateInviteView, AcceptInviteView,
    StoreMemberViewSet, ToggleMemberActiveView, RemoveMemberView, PendingInvitesView,
)

member_list = StoreMemberViewSet.as_view({"get": "list"})

urlpatterns = [
    path("register/", MerchantRegistrationView.as_view(), name="merchant-register"),
    path("invites/", CreateInviteView.as_view(), name="create-invite"),
    path("invites/accept/", AcceptInviteView.as_view(), name="accept-invite"),
    path("invites/pending/", PendingInvitesView.as_view(), name="pending-invites"),
    path("members/", member_list, name="member-list"),
    path("members/<int:membership_id>/toggle-active/", ToggleMemberActiveView.as_view(), name="toggle-member-active"),
    path("members/<int:membership_id>/", RemoveMemberView.as_view(), name="remove-member"),
]