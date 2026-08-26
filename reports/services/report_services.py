from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q

from apps.inventory.models import Transaction, Product, Store, Clerk

from django.utils import timezone


class ReportService:

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

        elif period == "monthly":
            start_date = today.replace(day=1)

        elif period == "annual":
            start_date = today.replace(
                month=1,
                day=1
            )

        else:
            raise ValueError("Invalid reporting period.")

        return start_date, today

    @staticmethod
    def inventory_report(period):
        """
        Inventory report - shows product stock levels and movements.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        products = Product.objects.all()
        
        data = []
        for product in products:
            transactions = Transaction.objects.filter(
                product=product,
                created_at__date__range=[start_date, end_date]
            )
            
            sales_qty = transactions.filter(
                transaction_type='SALE'
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            purchases_qty = transactions.filter(
                transaction_type='PURCHASE'
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            data.append({
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "current_stock": product.quantity_in_stock,
                "sales_qty": sales_qty,
                "purchases_qty": purchases_qty,
                "price": str(product.price),
            })
        Inventory report.
        """

        start_date, end_date = ReportService.get_period_dates(
            period
        )

        return {
            "report": "inventory",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_products": len(data),
            "data": data,
            "data": [],
        }

    @staticmethod
    def product_performance(period):
        """
        Product performance report - shows sales metrics by product.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        transactions = Transaction.objects.filter(
            transaction_type='SALE',
            created_at__date__range=[start_date, end_date]
        ).select_related('product')

        # Aggregate by product
        product_sales = {}
        for transaction in transactions:
            product = transaction.product
            if product.id not in product_sales:
                product_sales[product.id] = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "total_quantity": 0,
                    "total_revenue": Decimal('0'),
                    "transaction_count": 0,
                }
            product_sales[product.id]["total_quantity"] += transaction.quantity
            product_sales[product.id]["total_revenue"] += transaction.amount
            product_sales[product.id]["transaction_count"] += 1

        # Calculate average and convert to string
        data = []
        for product_id, sales_data in product_sales.items():
            avg_transaction = (
                sales_data["total_revenue"] / sales_data["transaction_count"]
                if sales_data["transaction_count"] > 0 else 0
            )
            data.append({
                **sales_data,
                "total_revenue": str(sales_data["total_revenue"]),
                "avg_transaction_value": str(avg_transaction),
            })

        # Sort by total revenue
        data.sort(key=lambda x: float(x["total_revenue"]), reverse=True)
        Product performance report.
        """

        start_date, end_date = ReportService.get_period_dates(
            period
        )

        return {
            "report": "product_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_products": len(data),
            "data": data,
            "data": [],
        }

    @staticmethod
    def store_performance(period):
        """
        Store performance report - shows sales metrics by store.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        stores = Store.objects.all()
        data = []

        for store in stores:
            transactions = Transaction.objects.filter(
                store=store,
                transaction_type='SALE',
                created_at__date__range=[start_date, end_date]
            )

            total_sales = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
            total_transactions = transactions.count()
            avg_transaction = (
                total_sales / total_transactions if total_transactions > 0 else 0
            )

            # Clerk performance in this store
            clerk_sales = transactions.values('clerk').annotate(
                clerk_count=Count('id')
            ).count()

            data.append({
                "store_id": store.id,
                "store_name": store.name,
                "location": store.location,
                "total_sales": str(total_sales),
                "total_transactions": total_transactions,
                "avg_transaction_value": str(avg_transaction),
                "active_clerks": clerk_sales,
            })

        # Sort by total sales
        data.sort(key=lambda x: float(x["total_sales"]), reverse=True)
        Store performance report.
        """

        start_date, end_date = ReportService.get_period_dates(
            period
        )

        return {
            "report": "store_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_stores": len(data),
            "data": data,
            "data": [],
        }

    @staticmethod
    def clerk_performance(period):
        """
        Clerk performance report - shows sales metrics by clerk.
        """
        start_date, end_date = ReportService.get_period_dates(period)

        clerks = Clerk.objects.select_related('user', 'store')
        data = []

        for clerk in clerks:
            transactions = Transaction.objects.filter(
                clerk=clerk,
                transaction_type='SALE',
                created_at__date__range=[start_date, end_date]
            )

            total_sales = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
            total_transactions = transactions.count()
            avg_transaction = (
                total_sales / total_transactions if total_transactions > 0 else 0
            )

            data.append({
                "clerk_id": clerk.id,
                "clerk_name": clerk.user.get_full_name() or clerk.user.username,
                "employee_id": clerk.employee_id,
                "store_name": clerk.store.name,
                "total_sales": str(total_sales),
                "total_transactions": total_transactions,
                "avg_transaction_value": str(avg_transaction),
            })

        # Sort by total sales
        data.sort(key=lambda x: float(x["total_sales"]), reverse=True)
        Clerk performance report.
        """

        start_date, end_date = ReportService.get_period_dates(
            period
        )

        return {
            "report": "clerk_performance",
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_clerks": len(data),
            "data": data,
            "data": [],
        }
