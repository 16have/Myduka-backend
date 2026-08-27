from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.inventory.models import Product, SpoilageRecord, StockTransaction


class ReportService:
    """
    Reports are computed from apps.inventory.StockTransaction /
    SpoilageRecord — the models the inventory API actually writes to.
    """

    @staticmethod
    def get_period_dates(period):
        """
        Calculate the start and end date for a report.
        """
        today = timezone.now().date()

        if period == "weekly":
            start_date = today - timedelta(days=6)
        elif period == "monthly":
            start_date = today.replace(day=1)
        elif period == "annual":
            start_date = today.replace(month=1, day=1)
        else:
            raise ValueError("Invalid reporting period. Use 'weekly', 'monthly', or 'annual'.")

        return start_date, today

    @staticmethod
    def inventory_report(period, store=None):
        """
        Inventory report - shows product stock levels and movements.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        products = Product.objects.all()
        if store is not None:
            products = products.filter(store=store)

        data = []
        for product in products:
            transactions = StockTransaction.objects.filter(
                product=product,
                created_at__date__range=[start_date, end_date],
            )

            received_qty = transactions.filter(
                transaction_type=StockTransaction.TransactionType.RECEIVED
            ).aggregate(Sum("quantity"))["quantity__sum"] or 0

            sold_qty = transactions.filter(
                transaction_type=StockTransaction.TransactionType.SOLD
            ).aggregate(Sum("quantity"))["quantity__sum"] or 0

            spoiled_qty = SpoilageRecord.objects.filter(
                product=product,
                created_at__date__range=[start_date, end_date],
            ).aggregate(Sum("quantity"))["quantity__sum"] or 0

            data.append({
                "product_id": product.id,
                "product_name": product.name,
                "current_stock": product.current_stock,
                "received_qty": received_qty,
                "sold_qty": sold_qty,
                "spoiled_qty": spoiled_qty,
                "selling_price": str(product.selling_price),
            })

        return {
            "report": "inventory",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_products": len(data),
            "data": data,
        }

    @staticmethod
    def product_performance(period, store=None):
        """
        Product performance report - shows sales metrics by product.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        transactions = StockTransaction.objects.filter(
            transaction_type=StockTransaction.TransactionType.SOLD,
            created_at__date__range=[start_date, end_date],
        ).select_related("product")
        if store is not None:
            transactions = transactions.filter(product__store=store)

        product_sales = {}
        for transaction in transactions:
            product = transaction.product
            if product.id not in product_sales:
                product_sales[product.id] = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "total_quantity": 0,
                    "total_revenue": Decimal("0"),
                    "transaction_count": 0,
                }
            revenue = (transaction.selling_price or Decimal("0")) * transaction.quantity
            product_sales[product.id]["total_quantity"] += transaction.quantity
            product_sales[product.id]["total_revenue"] += revenue
            product_sales[product.id]["transaction_count"] += 1

        data = []
        for sales_data in product_sales.values():
            avg_transaction = (
                sales_data["total_revenue"] / sales_data["transaction_count"]
                if sales_data["transaction_count"] > 0 else Decimal("0")
            )
            data.append({
                **sales_data,
                "total_revenue": str(sales_data["total_revenue"]),
                "avg_transaction_value": str(avg_transaction),
            })

        data.sort(key=lambda x: float(x["total_revenue"]), reverse=True)

        return {
            "report": "product_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_products": len(data),
            "data": data,
        }

    @staticmethod
    def store_performance(period, store=None):
        """
        Store performance report - shows sales metrics by store.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        stores = [store] if store is not None else []
        data = []

        for s in stores:
            transactions = StockTransaction.objects.filter(
                product__store=s,
                transaction_type=StockTransaction.TransactionType.SOLD,
                created_at__date__range=[start_date, end_date],
            )

            total_sales = sum(
                (t.selling_price or Decimal("0")) * t.quantity for t in transactions
            )
            total_transactions = transactions.count()
            avg_transaction = (
                total_sales / total_transactions if total_transactions > 0 else Decimal("0")
            )
            active_clerks = transactions.values("clerk").distinct().count()

            data.append({
                "store_id": s.id,
                "store_name": s.name,
                "total_sales": str(total_sales),
                "total_transactions": total_transactions,
                "avg_transaction_value": str(avg_transaction),
                "active_clerks": active_clerks,
            })

        return {
            "report": "store_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_stores": len(data),
            "data": data,
        }

    @staticmethod
    def clerk_performance(period, store=None):
        """
        Clerk performance report - shows sales metrics by clerk.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        transactions = StockTransaction.objects.filter(
            transaction_type=StockTransaction.TransactionType.SOLD,
            created_at__date__range=[start_date, end_date],
        ).select_related("clerk")
        if store is not None:
            transactions = transactions.filter(product__store=store)

        clerk_sales = {}
        for transaction in transactions:
            clerk = transaction.clerk
            if clerk.id not in clerk_sales:
                clerk_sales[clerk.id] = {
                    "clerk_id": clerk.id,
                    "clerk_name": clerk.name or clerk.email,
                    "total_sales": Decimal("0"),
                    "total_transactions": 0,
                }
            revenue = (transaction.selling_price or Decimal("0")) * transaction.quantity
            clerk_sales[clerk.id]["total_sales"] += revenue
            clerk_sales[clerk.id]["total_transactions"] += 1

        data = []
        for sales_data in clerk_sales.values():
            avg_transaction = (
                sales_data["total_sales"] / sales_data["total_transactions"]
                if sales_data["total_transactions"] > 0 else Decimal("0")
            )
            data.append({
                **sales_data,
                "total_sales": str(sales_data["total_sales"]),
                "avg_transaction_value": str(avg_transaction),
            })

        data.sort(key=lambda x: float(x["total_sales"]), reverse=True)

        return {
            "report": "clerk_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_clerks": len(data),
            "data": data,
        }
