from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Inventory, Product, SpoilageRecord, StockTransaction, SupplyRequest
from .serializers import (
    InventorySerializer,
    ProductSerializer,
    SpoilageRecordSerializer,
    StockTransactionSerializer,
    SupplyRequestSerializer,
)


def _get_user_from_request(request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return None
    try:
        from apps.accounts.models import User
        return User.objects.get(id=int(user_id))
    except (TypeError, ValueError, User.DoesNotExist):
        return None


class ProductListAPIView(APIView):
    def get(self, request):
        products = Product.objects.all().order_by("name")
        serializer = ProductSerializer(products, many=True)
        return Response({"success": True, "data": serializer.data})


class ProductDetailAPIView(APIView):
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProductSerializer(product)
        return Response({"success": True, "data": serializer.data})


class InventoryStatsAPIView(APIView):
    def get(self, request):
        products = Product.objects.all()
        unpaid = StockTransaction.objects.filter(payment_status="Not Paid").count()
        pending_requests = SupplyRequest.objects.filter(status="Pending").count()

        data = {
            "total_products": products.count(),
            "total_stock": sum(p.current_stock for p in products),
            "low_stock": sum(1 for p in products if p.stock_status == "Low Stock"),
            "out_of_stock": sum(1 for p in products if p.stock_status == "Out of Stock"),
            "unpaid_stock": unpaid,
            "pending_supply_requests": pending_requests,
        }
        return Response({"success": True, "data": data})


class ReceiveStockAPIView(APIView):
    def post(self, request):
        user = _get_user_from_request(request)
        if user is None:
            return Response(
                {"success": False, "message": "Authentication required (missing X-User-Id)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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
            product = Product.objects.get(id=product_id)
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
                    clerk=user,
                    transaction_type="Received",
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

        serializer = StockTransactionSerializer(txn)
        result = serializer.data
        result["new_stock_level"] = new_level
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class ReceivedStockListAPIView(APIView):
    def get(self, request):
        transactions = StockTransaction.objects.filter(transaction_type="Received").order_by("-created_at")
        serializer = StockTransactionSerializer(transactions, many=True)
        return Response({"success": True, "data": serializer.data})


class SpoilageListCreateAPIView(APIView):
    def get(self, request):
        records = SpoilageRecord.objects.all().order_by("-created_at")
        serializer = SpoilageRecordSerializer(records, many=True)
        return Response({"success": True, "data": serializer.data})

    def post(self, request):
        user = _get_user_from_request(request)
        if user is None:
            return Response(
                {"success": False, "message": "Authentication required (missing X-User-Id)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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
            product = Product.objects.get(id=product_id)
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
                    inventory = Inventory.objects.create(
                        product=product, quantity=0, current_stock=0
                    )
                inventory.current_stock = new_level
                inventory.quantity = new_level
                inventory.save()

                spoilage = SpoilageRecord.objects.create(
                    product=product,
                    quantity=qty,
                    reason=reason,
                    notes=data.get("notes"),
                    recorder=user,
                )
        except Exception:
            return Response(
                {"success": False, "message": "Could not record spoilage. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = SpoilageRecordSerializer(spoilage)
        result = serializer.data
        result["new_stock_level"] = new_level
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class SupplyRequestListCreateAPIView(APIView):
    def get(self, request):
        query = SupplyRequest.objects.all().order_by("-created_at")
        requested_by = request.query_params.get("requested_by")
        if requested_by:
            try:
                query = query.filter(requested_by=int(requested_by))
            except ValueError:
                return Response(
                    {"success": False, "message": "requested_by must be a number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = SupplyRequestSerializer(query, many=True)
        return Response({"success": True, "data": serializer.data})

    def post(self, request):
        user = _get_user_from_request(request)
        if user is None:
            return Response(
                {"success": False, "message": "Authentication required (missing X-User-Id)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        supply_request = SupplyRequest.objects.create(
            product=product,
            requested_by=user,
            quantity=int(quantity),
            reason=str(reason).strip(),
            notes=data.get("notes"),
            status="Pending",
        )
        serializer = SupplyRequestSerializer(supply_request)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)


class SupplyRequestUpdateAPIView(APIView):
    def put(self, request, request_id):
        user = _get_user_from_request(request)
        if user is None:
            return Response(
                {"success": False, "message": "Authentication required (missing X-User-Id)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.role != "admin":
            return Response(
                {"success": False, "message": "Only administrators can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            supply_request = SupplyRequest.objects.get(id=request_id)
        except SupplyRequest.DoesNotExist:
            return Response(
                {"success": False, "message": "Supply request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if supply_request.status != "Pending":
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

        serializer = SupplyRequestSerializer(supply_request)
        return Response({"success": True, "data": serializer.data})


class UnpaidPaymentsListAPIView(APIView):
    def get(self, request):
        transactions = StockTransaction.objects.filter(payment_status="Not Paid").order_by("-created_at")
        serializer = StockTransactionSerializer(transactions, many=True)
        return Response({"success": True, "data": serializer.data})


class PaymentStatusUpdateAPIView(APIView):
    def put(self, request, transaction_id):
        user = _get_user_from_request(request)
        if user is None:
            return Response(
                {"success": False, "message": "Authentication required (missing X-User-Id)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.role != "admin":
            return Response(
                {"success": False, "message": "Only administrators can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            transaction = StockTransaction.objects.get(id=transaction_id)
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

        transaction.payment_status = payment_status
        transaction.save()

        serializer = StockTransactionSerializer(transaction)
        return Response({"success": True, "data": serializer.data})
