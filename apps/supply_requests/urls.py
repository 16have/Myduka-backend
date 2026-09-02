from rest_framework.routers import DefaultRouter
from .views import SupplyRequestViewSet

router = DefaultRouter()
router.register(r"supply-requests", SupplyRequestViewSet, basename="supply-request")

urlpatterns = router.urls