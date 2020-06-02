import json
from datetime import datetime

from client_service_b.constants import FREQUENCY_CHOICES_REVERSE
from datastorage.models import RecurrentOrderContainer
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)
from internal_reports.utils import(
    filter_queryset_by_date_range,
    format_date_short_or_none
)
from tools.dates import format_date_long, read_date_short


class ReporterRecurrentOrders:
    """
    Reporter for recurrent orders
    """
    def __init__(self, context,
                 start_date, end_date, direct_debit, period_finished):
        """
        Initialise recurrent orders reporter
        :param context: AppContext instance
        :param start_date: string date for filtering recurrent orders
        :param end_date: string date for filtering recurrent orders
        :param direct_debit: value for filtering recurrent orders
        :param period_finished: value for filtering recurrent orders
        """

        self.context = context
        self.start_date = read_date_short(start_date) if start_date else None
        self.end_date = read_date_short(end_date) if end_date else None
        self.direct_debit = direct_debit
        self.period_finished = period_finished
        self.data = list()
        self.internal_report = None

    def run(self, internal_report):
        """
        Generate report with recurrent orders
        """

        recurrent_orders = RecurrentOrderContainer.objects.filter(
            user__app_context=self.context)

        self.internal_report = internal_report

        recurrent_orders = filter_queryset_by_date_range(
            recurrent_orders, self.start_date, self.end_date, 'created')

        if self.direct_debit:
            recurrent_orders = recurrent_orders.filter(
                direct_debit=self.direct_debit)

        if self.period_finished:
            recurrent_orders = recurrent_orders.filter(
                period_finished=self.period_finished)

        self.prepare_recurrent_orders_data(recurrent_orders)

        if self.data:
            self.data = sorted(self.data, key=lambda k: k['user_id'])
            self.internal_report.data = json.dumps(self.data,
                                                   indent=4)
            self.internal_report.status = INTERNAL_REPORT_STATUS_READY
            self.internal_report.generated = datetime.now()

        else:
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = 'No users with recurrent_order'

        self.internal_report.save()

    def prepare_recurrent_orders_data(self, recurrent_orders):
        """
        Generate report entry for user

        :param recurrent_orders: RecurrentOrderContainer queryset
        """

        for recurrent_order in recurrent_orders:
            self.data.append(dict(
                user_id=recurrent_order.user.app_uid,
                status=recurrent_order.status.name,
                amount=recurrent_order.amount,
                frequency_type=FREQUENCY_CHOICES_REVERSE.get(
                    int(recurrent_order.frequency_type), None),
                frequency=recurrent_order.frequency,
                order_start_date=format_date_short_or_none(
                    recurrent_order.order_start_date),
                order_next_date=format_date_short_or_none(
                    recurrent_order.order_next_date),
                order_end_date=format_date_short_or_none(
                    recurrent_order.order_end_date),
                action=recurrent_order.action,
                orders_created=recurrent_order.orders_created,
                number_of_retries=recurrent_order.number_of_retries,
                direct_debit=recurrent_order.direct_debit,
                created=format_date_long(recurrent_order.created),
                mandate_id=recurrent_order.mandate_id,
                direct_debit_date=format_date_short_or_none(
                    recurrent_order.direct_debit_date),
                cancel_after_next_execution=
                recurrent_order.cancel_after_next_execution,
            )
            )
