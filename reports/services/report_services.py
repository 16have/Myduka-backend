from datetime import timedelta

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
            "data": [],
        }

    @staticmethod
    def product_performance(period):
        """
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
            "data": [],
        }

    @staticmethod
    def store_performance(period):
        """
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
            "data": [],
        }

    @staticmethod
    def clerk_performance(period):
        """
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
            "data": [],
        }
