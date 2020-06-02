from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from datetime import datetime, timedelta

from api_campany.errors import WrongParameterError
from internal_reports.errors import (
    NoInternalReportError,
    CanNotDownloadReportError
)
from internal_reports.generator import start_report_generating
from internal_reports.models import InternalReport
from internal_reports.serializers import (
    InternalReportSerializer,
    InternalReportDetailedSerializer,
    InternalReportListRequestSerializer
)
from tools.dates import format_date_short
from permission.decorators import drf_extra_parameters
from .constants import *
from .view_set_parameters import *
from .utils import (
    get_end_date_from_request,
    get_date,
    get_required_int_value,
    get_file_format_from_request,
    prepare_response,
    get_int_value,
    get_date_from_request,
    check_for_true_false_all,
    format_date_short_or_none
)


class GenerateActiveUsersView(ViewSet):
    """
    Generate report with active users
    """

    @drf_extra_parameters(GENERATE_ACTIVE_USERS_PARAMETERS_LIST)
    def generate_active_users_list(self, request):
        """
        Start report generating with active users

        :param request: Request from client side

        :return: Response with active users
        """

        context = request.user.appcontextmembers.context

        parameters = request.query_params
        start_date = get_date(parameters.get(
            'start_date', None), 'start_date')
        end_date = get_date(parameters.get(
            'end_date', None), 'end_date')
        consecutive_days = get_required_int_value(parameters.get(
            'consecutive_days', None), 'consecutive_days')
        amount_to_validate = get_required_int_value(parameters.get(
            'amount_to_validate', None), 'amount_to_validate')

        return start_report_generating(
            context,
            INTERNAL_REPORT_ACTIVE_USERS,
            input_data=dict(
                start_date=format_date_short(start_date),
                end_date=format_date_short(end_date),
                consecutive_days=consecutive_days,
                amount_to_validate=amount_to_validate
            )
        )


class GenerateUsersRiskScoreView(ViewSet):

    @drf_extra_parameters(GENERATE_USERS_RISK_SCORE_PARAMETERS_LIST)
    def generate_users_risk_score_list(self, request):
        """
        Start report generating with users risk score

        ---
        """

        parameters = request.query_params

        context = request.user.appcontextmembers.context

        upper_risk_score = get_int_value(parameters.get('upper_risk_score'))
        lower_risk_score = get_int_value(parameters.get('lower_risk_score'))

        return start_report_generating(
            context,
            INTERNAL_REPORT_USER_RISK_SCORES,
            input_data=dict(
                upper_risk_score=upper_risk_score,
                lower_risk_score=lower_risk_score
            )
        )


class QuarterDataValidationView(ViewSet):
    """
    Generate report after validation of quarter reports data
    """

    @drf_extra_parameters(GENERATE_VALIDATED_QUARTER_REPORT_DATA)
    def validate_quarter_data(self, request):
        """
        Start report generating with invalid quarter reports
        :param request: Request from client side
        :return: Response with data for users who did not pass validation

        ---
        """

        parameters = request.query_params
        end_date = get_end_date_from_request(parameters)
        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_QUARTER_VALIDATION,
            input_data=dict(
                end_date=format_date_short(end_date)
            )
        )


class GoalsReportView(ViewSet):
    """
    Generate goals report
    """

    @staticmethod
    @drf_extra_parameters(GENERATE_GOALS_PARAMETERS_LIST)
    def get_goals_report(request):
        """
        Start report generating with users goals

        :param request: Request from client side

        :return: Response with data for users who did not pass validation
        """

        parameters = request.query_params
        start_date = get_date_from_request(parameters, 'start_date')
        end_date = get_date_from_request(parameters, 'end_date')
        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_GOALS,
            input_data=dict(
                start_date=format_date_short_or_none(start_date),
                end_date=format_date_short_or_none(end_date)
            )
        )


class GenerateOrdersView(ViewSet):
    """
    Generate orders report
    """

    @staticmethod
    @drf_extra_parameters(GENERATE_ORDERS_PARAMETERS_LIST)
    def generate_orders(request):
        """
        Start report generating with users orders

        :param request: Request from client side

        :return: Response with data for users who have orders
        """

        parameters = request.query_params
        start_date = get_date_from_request(parameters, 'start_date')
        end_date = get_date_from_request(parameters, 'end_date')
        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_ORDERS,
            input_data=dict(
                start_date=format_date_short_or_none(start_date),
                end_date=format_date_short_or_none(end_date)
            )
        )


class GenerateRecurrentOrdersView(ViewSet):
    """
    Generate recurrent orders report
    """

    @staticmethod
    @drf_extra_parameters(GENERATE_RECURRENT_ORDERS_PARAMETERS_LIST)
    def generate_recurrent_orders(request):
        """
        Start report generating with users recurrent orders

        :param request: Request from client side

        :return: Response with data for users who have recurrent orders
        """

        parameters = request.query_params
        start_date = get_date_from_request(parameters, 'start_date')
        end_date = get_date_from_request(parameters, 'end_date')
        direct_debit = check_for_true_false_all(parameters, 'direct_debit')
        period_finished = check_for_true_false_all(parameters, 'period_finished')
        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_RECURRENT_ORDERS,
            input_data=dict(
                start_date=format_date_short_or_none(start_date),
                end_date=format_date_short_or_none(end_date),
                direct_debit=direct_debit,
                period_finished=period_finished
            )
        )


class GenerateBalancesView(ViewSet):
    """
    Generate balamce report
    """

    @staticmethod
    def generate_balances(request):
        """
        Start report generating with asset container balances

        :param request: Request from client side

        :return: Response with data for asset container balances
        """

        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_BALANCES,
        )


class GenerateAssetsView(ViewSet):
    """
    Generate report with active users
    """

    def generate_assets_list(self, request):
        """
        Start report generating with assets

        :param request: Request from client side

        :return: Response with assets
        """

        context = request.user.appcontextmembers.context

        return start_report_generating(
            context,
            INTERNAL_REPORT_ASSETS,
        )


class GetReportsListView(ViewSet):

    @staticmethod
    def get_all(request):
        """
        Get list of internal reports

        ---
        parameter:
        - name: start_date
          description: start of time period (YYYY-MM-DD)
          type: string
          required: false
          location: query
        - name: end_date
          description: end of time period (YYYY-MM-DD)
          type: string
          required: false
          location: query
        - name: type
          description: type of internal report
          type: integer
          required: false
          location: query
        - name: status
          description: status of internal report
          type: integer
          required: false
          location: query
        """

        serializer = InternalReportListRequestSerializer(
            data=request.query_params
        )
        if not serializer.is_valid():
            raise WrongParameterError(description=serializer.errors)

        data = serializer.data

        context = request.user.appcontextmembers.context

        raw_filters = dict(
            context=context,
            generated__gte=serializer.get_start_date(),
            generated__lte=serializer.get_end_date(),
            type=data.get('type', None),
            status=data.get('status', None)
        )

        filters = [Q(**{k: v}) for k, v in raw_filters.items() if v is not None]

        reports = InternalReport.objects.filter(*filters).order_by('-generated')

        broken_reports = reports.filter(
            status=INTERNAL_REPORT_STATUS_GENERATING,
            generated__lt=datetime.now() - timedelta(hours=24))

        if len(broken_reports):
            broken_reports.update(status=INTERNAL_REPORT_STATUS_FAILED)

        return Response(
            data=InternalReportSerializer(reports, many=True).data,
            status=status.HTTP_200_OK
        )


class GetReportView(ViewSet):

    @staticmethod
    def get_detailed_report(request):
        """
        View internal report data

        ---
        parameter:
        - name: report_id
          description: report_id
          type: integer
          required: true
          location: query
        """

        report_id = request.query_params.get('report_id', None)

        try:
            report = InternalReport.objects.get(pk=report_id)
        except InternalReport.DoesNotExist:
            raise NoInternalReportError

        return Response(
            data=InternalReportDetailedSerializer(report).data,
            status=status.HTTP_200_OK
        )


class DownloadReportView(ViewSet):

    @staticmethod
    def download_report(request):
        """
        Prepare data in specific format

        ---
        parameter:
        - name: report_id
          description: report_id
          type: integer
          required: true
          location: query
        - name: file_format
          description: file_format
          type: string
          required: false
          location: query
        """

        file_format = get_file_format_from_request(request.query_params)
        report_id = request.query_params.get('report_id', None)

        try:
            report = InternalReport.objects.get(pk=report_id)
        except InternalReport.DoesNotExist:
            raise NoInternalReportError

        if report.status is not INTERNAL_REPORT_STATUS_READY:
            raise CanNotDownloadReportError

        return prepare_response(
            report=report,
            file_format=file_format,
        )


class GetReportsTypesView(ViewSet):

    @staticmethod
    def get_types(request):
        """
        Get internal report types

        ---
        """

        data = list()

        for entry in INTERNAL_REPORT_TYPES:
            data.append(dict(
                type=entry[0],
                name=entry[1]
            ))

        return Response(
            data=data,
            status=status.HTTP_200_OK
        )


class GetReportStatusesView(ViewSet):
    @staticmethod
    def get_statuses(request):
        """
        Get internal report statuses

        ---
        """

        data = list()

        for entry in INTERNAL_REPORT_STATUSES:
            data.append(dict(
                type=entry[0],
                name=entry[1]
            ))

        return Response(
            data=data,
            status=status.HTTP_200_OK
        )
