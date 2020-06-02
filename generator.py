import json

from rest_framework import status
from rest_framework.response import Response

from internal_reports.reports.assets import ReporterAssets
from serviceAPI.celery import app
from internal_reports.constants import *
from internal_reports.models import InternalReport
from internal_reports.reports.active_users_list import ReporterActiveUsersList
from internal_reports.reports.balances import ReporterBalances
from internal_reports.reports.goals_report import ReporterGoals
from internal_reports.reports.orders import ReporterOrders
from internal_reports.reports.recurrent_orders import ReporterRecurrentOrders
from internal_reports.reports.users_risk_score import ReporterRiskScoreUsersList
from internal_reports.serializers import InternalReportSerializer
from internal_reports.reports.validate_quarter_data import (
    ReporterInvalidQuarterData
)


def start_report_generating(context, report_type, input_data=None):
    """
    Trigger internal report generating

    :param context: AppContext instance
    :param report_type: Report type
    :param input_data: dictionary with report input data

    :return: Response with internal report object
    """

    internal_report = InternalReport.objects.create(
        context=context,
        type=report_type,
        status=INTERNAL_REPORT_STATUS_GENERATING,
        input_data=json.dumps(input_data or {})
    )

    generate_report_in_background.delay(internal_report.id)

    return Response(
        data=InternalReportSerializer(internal_report).data,
        status=status.HTTP_202_ACCEPTED
    )


@app.task
def generate_report_in_background(internal_report_id):
    """
    Start internal report generating as Celery task

    :param internal_report_id: ID of internal report that is generated
    """

    internal_report = InternalReport.objects.get(pk=internal_report_id)
    generator = {
        INTERNAL_REPORT_ACTIVE_USERS: ReporterActiveUsersList,
        INTERNAL_REPORT_USER_RISK_SCORES: ReporterRiskScoreUsersList,
        INTERNAL_REPORT_QUARTER_VALIDATION: ReporterInvalidQuarterData,
        INTERNAL_REPORT_GOALS: ReporterGoals,
        INTERNAL_REPORT_RECURRENT_ORDERS: ReporterRecurrentOrders,
        INTERNAL_REPORT_ORDERS: ReporterOrders,
        INTERNAL_REPORT_BALANCES: ReporterBalances,
        INTERNAL_REPORT_ASSETS: ReporterAssets
    }
    generator[internal_report.type](
        context=internal_report.context,
        **json.loads(internal_report.input_data)
    ).run(internal_report)
