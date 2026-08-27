from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStoreAdmin

from .models import Inventory, Product, SpoilageRecord, StockTransaction, SupplyRequest
from .serializers import (
    ErrorSerializer,
    InventoryStatsSerializer,
    PaymentStatusUpdateRequestSerializer,
    ProductCreateSerializer,
    ProductSerializer,
    ReceiveStockRequestSerializer,
    SellStockRequestSerializer,
    SpoilageRecordResultSerializer,
    SpoilageRecordSerializer,
    SpoilageRequestSerializer,
    StockTransactionResultSerializer,
    StockTransactionSerializer,
    SupplyRequestCreateSerializer,
    SupplyRequestDecisionSerializer,
    SupplyRequestSerializer,
)


@extend_schema(tags=["Inventory"])
class ProductListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProductSerializer(many=True)})
    def get(self, request):
        products = Product.objects.filter(store=request.user.store).order_by("name")
        serializer = ProductSerializer(products, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        request=ProductCreateSerializer,
        responses={201: ProductSerializer, 400: ErrorSerializer, 403: ErrorSerializer},
    )
    def post(self, request):
        if not IsStoreAdmin().has_permission(request, self):
            return Response(
                {"success": False, "message": "Only administrators can add products."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        name = str(data.get("name", "")).strip()
        buying_price = data.get("buying_price")
        selling_price = data.get("selling_price")
        if not name or buying_price is None or selling_price is None:
            return Response(
                {"success": False, "message": "name, buying_price and selling_price are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = Product.objects.create(
            store=request.user.store,
            name=name,
            description=data.get("description", ""),
            category=data.get("category", ""),
            buying_price=buying_price,
            selling_price=selling_price,
            minimum_stock_level=data.get("minimum_stock_level", 0),
        )
        Inventory.objects.create(product=product, quantity=0, current_stock=0)
        return Response(
            {"success": True, "data": ProductSerializer(product).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Inventory"])
class ProductDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProductSerializer, 404: ErrorSerializer})
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "data": ProductSerializer(product).data})


@extend_schema(tags=["Inventory"])
class InventoryStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: InventoryStatsSerializer})
    def get(self, request):
        products = Product.objects.filter(store=request.user.store)
        unpaid = StockTransaction.objects.filter(
            product__store=request.user.store, payment_status="Not Paid"
        ).count()
        pending_requests = SupplyRequest.objects.filter(
            product__store=request.user.store, status="Pending"
        ).count()

        data = {
            "total_products": products.count(),
            "total_stock": sum(p.current_stock for p in products),
            "low_stock": sum(1 for p in products if p.stock_status == "Low Stock"),
            "out_of_stock": sum(1 for p in products if p.stock_status == "Out of Stock"),
            "unpaid_stock": unpaid,
            "pending_supply_requests": pending_requests,
        }
        return Response({"success": True, "data": data})


@extend_schema(tags=["Inventory"])
class ReceiveStockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReceiveStockRequestSerializer,
        responses={201: StockTransactionResultSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
    )
    def post(self, request):
        data = request.data

        product_id = data.get("product_id")
        quantity = data.get("quantity")
        buying_price = data.get("buying_price")
        selling_price = data.get("selling_price")
        payment_status = data.get("payment_status")

        if not all([product_id, quantity, buying_price, selling_price, payment_status]):
            return Response(
                {"success": False, "message": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_status not in ("Paid", "Not Paid"):
            return Response(
                {"success": False, "message": "payment_status must be one of: Paid, Not Paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with transaction.atomic():
                new_level = product.current_stock + int(quantity)
                product.current_stock = new_level
                product.buying_price = buying_price
                product.selling_price = selling_price
                product.save()

                inventory, _ = Inventory.objects.get_or_create(
                    product=product,
                    defaults={"quantity": 0, "current_stock": 0},
                )
                inventory.current_stock = new_level
                inventory.quantity = new_level
                inventory.save()

                last_txn = StockTransaction.objects.order_by("-id").first()
                next_id = (last_txn.id + 1) if last_txn else 1
                reference_number = f"RCV-{next_id:04d}"

                txn = StockTransaction.objects.create(
                    product=product,
                    clerk=request.user,
                    transaction_type=StockTransaction.TransactionType.RECEIVED,
                    quantity=int(quantity),
                    buying_price=buying_price,
                    selling_price=selling_price,
                    payment_status=payment_status,
                    supplier=data.get("supplier"),
                    notes=data.get("notes"),
                    reference_number=reference_number,
                )
        except Exception:
            return Response(
                {"success": False, "message": "Could not save the received stock. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result = StockTransactionSerializer(txn).data
        result["new_stock_level"] = new_level
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Inventory"])
class ReceivedStockListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: StockTransactionSerializer(many=True)})
    def get(self, request):
        transactions = StockTransaction.objects.filter(
            product__store=request.user.store,
            transaction_type=StockTransaction.TransactionType.RECEIVED,
        ).order_by("-created_at")
        return Response({"success": True, "data": StockTransactionSerializer(transactions, many=True).data})


@extend_schema(tags=["Inventory"])
class SellStockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SellStockRequestSerializer,
        responses={201: StockTransactionResultSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        data = request.data
        product_id = data.get("product_id")
        quantity = data.get("quantity")
        payment_status = data.get("payment_status", "Paid")

        if not all([product_id, quantity]):
            return Response(
                {"success": False, "message": "product_id and quantity are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_status not in ("Paid", "Not Paid"):
            return Response(
                {"success": False, "message": "payment_status must be one of: Paid, Not Paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qty = int(quantity)
        if qty > product.current_stock:
            return Response(
                {"success": False, "message": f"Cannot sell {qty}: only {product.current_stock} unit(s) in stock."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                new_level = product.current_stock - qty
                product.current_stock = new_level
                product.save()

                inventory = getattr(product, "inventory", None)
                if inventory is None:
                    inventory = Inventory.objects.create(product=product, quantity=0, current_stock=0)
                inventory.current_stock = new_level
                inventory.quantity = new_level
                inventory.save()

                last_txn = StockTransaction.objects.order_by("-id").first()
                next_id = (last_txn.id + 1) if last_txn else 1
                reference_number = f"SLD-{next_id:04d}"

                txn = StockTransaction.objects.create(
                    product=product,
                    clerk=request.user,
                    transaction_type=StockTransaction.TransactionType.SOLD,
                    quantity=qty,
                    selling_price=product.selling_price,
                    payment_status=payment_status,
                    notes=data.get("notes"),
                    reference_number=reference_number,
                )
        except Exception:
            return Response(
                {"success": False, "message": "Could not record the sale. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result = StockTransactionSerializer(txn).data
        result["new_stock_level"] = new_level
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Inventory"])
class SpoilageListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SpoilageRecordSerializer(many=True)})
    def get(self, request):
        records = SpoilageRecord.objects.filter(product__store=request.user.store).order_by("-created_at")
        return Response({"success": True, "data": SpoilageRecordSerializer(records, many=True).data})

    @extend_schema(
        request=SpoilageRequestSerializer,
        responses={201: SpoilageRecordResultSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        data = request.data
        product_id = data.get("product_id")
        quantity = data.get("quantity")
        reason = data.get("reason")

        if not all([product_id, quantity, reason]):
            return Response(
                {"success": False, "message": "Missing required fields: product_id, quantity, reason."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_reasons = dict(SpoilageRecord.Reason.choices)
        if reason not in valid_reasons:
            return Response(
                {"success": False, "message": f"reason must be one of: {', '.join(valid_reasons.keys())}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qty = int(quantity)
        if qty > product.current_stock:
            return Response(
                {"success": False, "message": f"Cannot record {qty} spoiled: only {product.current_stock} unit(s) in stock."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                new_level = product.current_stock - qty
                product.current_stock = new_level
                product.save()

                inventory = getattr(product, "inventory", None)
                if inventory is None:
                    inventory = Inventory.objects.create(product=product, quantity=0, current_stock=0)
                inventory.current_stock = new_level
                inventory.quantity = new_level
                inventory.save()

                spoilage = SpoilageRecord.objects.create(
                    product=product,
                    quantity=qty,
                    reason=reason,
                    notes=data.get("notes"),
                    recorder=request.user,
                )
        except Exception:
            return Response(
                {"success": False, "message": "Could not record spoilage. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result = SpoilageRecordSerializer(spoilage).data
        result["new_stock_level"] = new_level
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Inventory"])
class SupplyRequestListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SupplyRequestSerializer(many=True), 400: ErrorSerializer})
    def get(self, request):
        query = SupplyRequest.objects.filter(product__store=request.user.store).order_by("-created_at")
        requested_by = request.query_params.get("requested_by")
        if requested_by:
            try:
                query = query.filter(requester=int(requested_by))
            except ValueError:
                return Response(
                    {"success": False, "message": "requested_by must be a number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response({"success": True, "data": SupplyRequestSerializer(query, many=True).data})

    @extend_schema(
        request=SupplyRequestCreateSerializer,
        responses={201: SupplyRequestSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
    )
    def post(self, request):
        data = request.data
        product_id = data.get("product_id")
        quantity = data.get("quantity")
        reason = data.get("reason")

        if not all([product_id, quantity, reason]):
            return Response(
                {"success": False, "message": "Missing required fields: product_id, quantity, reason."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        supply_request = SupplyRequest.objects.create(
            product=product,
            requester=request.user,
            quantity=int(quantity),
            reason=str(reason).strip(),
            notes=data.get("notes"),
            status=SupplyRequest.Status.PENDING,
        )
        return Response(
            {"success": True, "data": SupplyRequestSerializer(supply_request).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Inventory"])
class SupplyRequestUpdateAPIView(APIView):
    permission_classes = [IsStoreAdmin]

    @extend_schema(
        request=SupplyRequestDecisionSerializer,
        responses={200: SupplyRequestSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def put(self, request, request_id):
        try:
            supply_request = SupplyRequest.objects.get(id=request_id, product__store=request.user.store)
        except SupplyRequest.DoesNotExist:
            return Response(
                {"success": False, "message": "Supply request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if supply_request.status != SupplyRequest.Status.PENDING:
            return Response(
                {"success": False, "message": f"Request #{request_id} was already {supply_request.status.lower()}."},
                status=status.HTTP_409_CONFLICT,
            )

        data = request.data
        status_value = data.get("status")
        if status_value not in ("Approved", "Declined"):
            return Response(
                {"success": False, "message": "status must be one of: Approved, Declined."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        supply_request.status = status_value
        supply_request.admin_response = data.get("admin_response")
        supply_request.save()

        return Response({"success": True, "data": SupplyRequestSerializer(supply_request).data})


@extend_schema(tags=["Inventory"])
class UnpaidPaymentsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: StockTransactionSerializer(many=True)})
    def get(self, request):
        transactions = StockTransaction.objects.filter(
            product__store=request.user.store, payment_status="Not Paid"
        ).order_by("-created_at")
        return Response({"success": True, "data": StockTransactionSerializer(transactions, many=True).data})


@extend_schema(tags=["Inventory"])
class PaymentStatusUpdateAPIView(APIView):
    permission_classes = [IsStoreAdmin]

    @extend_schema(
        request=PaymentStatusUpdateRequestSerializer,
        responses={200: StockTransactionSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
    )
    def put(self, request, transaction_id):
        try:
            txn = StockTransaction.objects.get(id=transaction_id, product__store=request.user.store)
        except StockTransaction.DoesNotExist:
            return Response(
                {"success": False, "message": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data
        payment_status = data.get("payment_status")
        if payment_status not in ("Paid", "Not Paid"):
            return Response(
                {"success": False, "message": "payment_status must be one of: Paid, Not Paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        txn.payment_status = payment_status
        txn.save()

        return Response({"success": True, "data": StockTransactionSerializer(txn).data})
