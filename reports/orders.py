import json
from datetime import datetime

from datastorage.models import Order
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)
from internal_reports.utils import(
    filter_queryset_by_date_range,
    format_date_short_or_none
)
from tools.dates import read_date_short


class ReporterOrders:
    """
    Reporter for orders
    """
    def __init__(self, context, start_date, end_date):
        """
        Initialise orders reporter
        :param context: AppContext instance
        :param start_date: string date for filtering orders
        :param end_date: string date for filtering orders
        """

        self.context = context
        self.start_date = read_date_short(start_date) if start_date else None
        self.end_date = read_date_short(end_date) if end_date else None
        self.data = list()
        self.internal_report = None

    def run(self, internal_report):
        """
        Generate report with orders
        """

        orders = Order.objects.filter(
            user__app_context=self.context)

        self.internal_report = internal_report

        orders = filter_queryset_by_date_range(
            orders, self.start_date, self.end_date, 'value_date')

        self.prepare_orders_data(orders)

        if self.data:
            self.data = sorted(self.data, key=lambda k: k['user_id'])
            self.internal_report.data = json.dumps(self.data,
                                                   indent=4)
            self.internal_report.status = INTERNAL_REPORT_STATUS_READY
            self.internal_report.generated = datetime.now()

        else:
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = 'No users with order'

        self.internal_report.save()

    def prepare_orders_data(self, orders):
        """
        Generate report entry for user

        :param orders: Orders queryset
        """

        for order in orders:
            self.data.append(dict(
                user_id=order.user.app_uid,
                type=order.action,
                date=format_date_short_or_none(order.value_date),
                value=order.value,
                status=order.get_status_display(),
                rebalancing=order.rebalancing
            ))
