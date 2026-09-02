from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, StockReceiptViewSet, SpoilageRecordViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"stock-receipts", StockReceiptViewSet, basename="stock-receipt")
router.register(r"spoilage", SpoilageRecordViewSet, basename="spoilage")

urlpatterns = router.urls