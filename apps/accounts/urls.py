from django.urls import path

from .views import (
    AdminRegistrationView,
    AdminsView,
    InvitationDetailView,
    InvitationsView,
    LoginView,
    LogoutView,
    MeView,
    UserActionView,
    ClerksView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("invitations", InvitationsView.as_view(), name="invitations"),
    path("invitations/<str:token>", InvitationDetailView.as_view(), name="invitation-detail"),
    path("register-admin", AdminRegistrationView.as_view(), name="register-admin"),
    path("admins", AdminsView.as_view(), name="admins"),
    path("admins/<int:user_id>/<str:action>", UserActionView.as_view(), name="admin-action"),
    path("clerks", ClerksView.as_view(), name="clerks"),
    path("clerks/<int:user_id>/<str:action>", UserActionView.as_view(), name="clerk-action"),
]