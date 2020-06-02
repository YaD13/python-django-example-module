import json
from datetime import datetime, timedelta, date
from multiprocessing.pool import ThreadPool

from django.conf import settings
from django.urls import reverse
from mock import patch
from rest_framework import status

from api_campany.errors import WrongParameterError
from client_analyze.utils import GearmanClient
from client_core_analyse.client.performance import (
    PerformanceGeometricPortfolioClient
)
from client_core_analyse.client_generic import CoreAnalyse2Client
from client_interact.client import CoreInteractClient
from client_interact.tests import (
    MockCoreInteractClient,
    MockCoreInteractClientEmptyResponse
)
from client_service_c.client import service_cClient
from client_service_c.constants import (
    STATUS_PENDING,
    INVESTMENT_CASH_COMPONENT,
    STATUS_ONGOING
)
from client_service_c.models import service_cRebalancingOrder
from client_service_c.tests import Basicservice_cTest
from client_service_c.utils.common import get_order_status
from client_service_c.views import RebalancingView
from datastorage.models import (
    Order,
    UserRiskProfile,
    RiskProfile,
    RecurrentOrderContainer
)
from historicals.utils import get_quarter_dates
from internal_reports.constants import (
    FILE_FORMAT_JSON,
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_ACTIVE_USERS,
    INTERNAL_REPORT_STATUS_GENERATING
)
from internal_reports.errors import (
    DatesForReportAreRequired,
    RequiredParameters,
    NoInternalReportError,
    CanNotDownloadReportError,
    ReportDataError,
    WrongFileFormat,
    WrongInputValue
)
from internal_reports.generator import generate_report_in_background
from internal_reports.models import InternalReport
from internal_reports.reports.active_users_list import ReporterActiveUsersList
from internal_reports.reports.assets import ReporterAssets
from internal_reports.reports.balances import ReporterBalances
from internal_reports.reports.goals_report import ReporterGoals
from internal_reports.reports.orders import ReporterOrders
from internal_reports.reports.recurrent_orders import ReporterRecurrentOrders
from internal_reports.reports.users_risk_score import ReporterRiskScoreUsersList
from internal_reports.reports.validate_quarter_data import (
    ReporterInvalidQuarterData
)
from internal_reports.views import (
    GenerateActiveUsersView,
    GenerateUsersRiskScoreView,
    QuarterDataValidationView,
    GoalsReportView,
    GetReportsListView,
    GetReportsTypesView,
    GetReportStatusesView,
    GetReportView,
    DownloadReportView,
    GenerateRecurrentOrdersView,
    GenerateOrdersView,
    GenerateBalancesView,
    GenerateAssetsView
)
from pdf.errors import (
    NoPortfolioHistory
)
from pdf.tests.utils import (
    get_portfolio_mock_history,
    MockAssetPerformanceRequest,
    get_portfolio_mock_history_warning,
)
from permission.constants import *
from permission.models import UserMapping, AppContext
from serviceAPI.settings import ISIN_CASH_COMPONENT, KEY_SELL
from serviceAPI.testing_clients import (
    Mockservice_cClient,
    MockAnalyseClientWithWarnings
)
from serviceAPI.testing_tools import (
    FakeError,
    FAKE_ISIN_1,
    FAKE_FUND_NAME_1,
    FAKE_ISIN_2,
    FAKE_FUND_NAME_2,
    FAKE_ISIN_3,
    FAKE_FUND_NAME_3,
    MockAnalyseClientCorrectRebalance,
    PoolWithoutThreads)
from serviceAPI.testing_utils import (
    create_user,
    assign_risk_profile,
    create_goal
)
from tools.dates import format_date_short


class InternalReportBasicTest(Basicservice_cTest):

    def view_report(self, report_id):
        url = reverse('internal:view')

        request = self.factory.get(url)
        request.user = self.service_c_user

        request.query_params = dict(report_id=report_id)

        view = GetReportView()

        return view.get_detailed_report(
            request=request,
        )

    def download_report(self, report_id, file_format=None):
        url = reverse('internal:download')

        request = self.factory.get(url)
        request.user = self.service_c_user

        request.query_params = dict(report_id=report_id)

        if file_format:
            request.query_params.update(file_format=file_format)

        return DownloadReportView().download_report(
            request=request,

        )


class ServiceEndpointsTest(InternalReportBasicTest):
    def test_types_endpoint(self):
        request = self.factory.get(reverse('internal:types'))
        request.user = self.service_c_user

        response = GetReportsTypesView().get_types(request=request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_statuses_endpoint(self):
        request = self.factory.get(reverse('internal:statuses'))
        request.user = self.service_c_user

        response = GetReportStatusesView().get_statuses(request=request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_not_existing_report(self):
        with self.assertRaises(NoInternalReportError):
            self.view_report(report_id=0)

    def test_not_existing_download(self):
        with self.assertRaises(NoInternalReportError):
            self.download_report(report_id=0)


class ActiveUsersReportTest(InternalReportBasicTest):

    def setUp(self):
        super(ActiveUsersReportTest, self).setUp()

        current_quarter_start = get_quarter_dates(datetime.now().date())[0]
        prev_quarter_end = current_quarter_start - timedelta(days=1)

        self.end_date = prev_quarter_end
        self.start_date = get_quarter_dates(self.end_date)[0]

        self.user_mapping.has_portfolio_history = True
        self.user_mapping.save()

        self.order = Order.objects.create(
            action='BUYI',
            status=STATUS_PENDING,
            user=self.user_mapping,
            amount=100,
            value_date=self.end_date
        )

        self.history = get_portfolio_mock_history(
            start_date=self.start_date,
            end_date=self.end_date,
            user_mapping=self.user_mapping
        )

        self.history_with_zeros = get_portfolio_mock_history(
            start_date=self.start_date,
            end_date=self.end_date,
            user_mapping=self.user_mapping,
            zero_quantity=True
        )

    def generate_report(
            self,
            start_date=format_date_short(datetime.now() - timedelta(days=90)),
            end_date=format_date_short(datetime.now()),
            consecutive_days=10,
            amount_to_validate=50):

        response = self.send_request(start_date, end_date, consecutive_days,
                                     amount_to_validate)

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterActiveUsersList(
            context=self.context,
            start_date=start_date,
            end_date=end_date,
            consecutive_days=consecutive_days,
            amount_to_validate=amount_to_validate
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self,
                     start_date=None,
                     end_date=None,
                     consecutive_days=None,
                     amount_to_validate=None):

        request = self.factory.get('internal:generate-active-users-list')
        request.user = self.service_c_user

        query_params = dict()

        if amount_to_validate:
            query_params.update(amount_to_validate=amount_to_validate)

        if start_date:
            query_params.update(start_date=start_date)

        if end_date:
            query_params.update(end_date=end_date)

        if consecutive_days:
            query_params.update(consecutive_days=consecutive_days)

        request.query_params = query_params

        view = GenerateActiveUsersView()

        return view.generate_active_users_list(request=request)

    def test_check_endpoint_no_dates(self):
        with self.assertRaises(DatesForReportAreRequired):
            self.send_request()

    def test_check_endpoint_with_dates(self):
        with self.assertRaises(RequiredParameters):
            self.send_request(
                start_date=format_date_short(datetime.now().date()),
                end_date=format_date_short(datetime.now().date())
            )

    def test_generate_active_users_list(self):

        def get_portfolio_history(*_, **__):
            return self.history

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            report = self.generate_report()

            response = self.view_report(report.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_active_users_list_without_history(self):

        def get_portfolio_history(*_, **__):
            raise NoPortfolioHistory

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            report = self.generate_report()

            response = self.view_report(report.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_active_users_list_with_zero_values_in_history(self):

        def get_portfolio_history(*_, **__):
            return self.history_with_zeros

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            report = self.generate_report()

            response = self.view_report(report.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_active_users_list_without_date(self):

        def get_portfolio_history(*_, **__):
            return self.history

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            with self.assertRaises(DatesForReportAreRequired):
                report = self.generate_report(start_date='')

                response = self.view_report(report.id)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_active_users_list_with_specific_history(self):

        end_date = datetime.today()
        start_date = end_date - timedelta(days=60)

        def get_portfolio_history(*_, **__):

            temp_date = start_date

            target_date = datetime.today() - timedelta(days=30)

            data = list()

            while temp_date <= end_date:
                if temp_date <= target_date:
                    price = 20
                else:
                    price = 10

                components = [
                    dict(
                        isin=FAKE_ISIN_1,
                        name=FAKE_FUND_NAME_1,
                        quantity=1,
                        price=None,
                        price_eur=price,
                        fx_rate=None,
                        ffill_used=True
                    ),
                    dict(
                        isin=FAKE_ISIN_2,
                        name=FAKE_FUND_NAME_2,
                        quantity=1,
                        price=None,
                        price_eur=price,
                        fx_rate=None,
                        ffill_used=True
                    ),
                    dict(
                        isin=FAKE_ISIN_3,
                        name=FAKE_FUND_NAME_3,
                        quantity=1,
                        price=None,
                        price_eur=price,
                        fx_rate=None,
                        ffill_used=True
                    ),
                    dict(
                        isin=ISIN_CASH_COMPONENT,
                        name=INVESTMENT_CASH_COMPONENT,
                        quantity=1,
                        price=1,
                        price_eur=1,
                        fx_rate=None,
                        ffill_used=False
                    )
                ]

                data.append(dict(
                    date=format_date_short(temp_date),
                    components=components
                ))

                temp_date += timedelta(days=1)

            return data

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            report = self.generate_report(
                consecutive_days=1,
                amount_to_validate=50,
                start_date=format_date_short(start_date),
                end_date=format_date_short(end_date)
            )
            response = self.view_report(report.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_active_users_list_with_broken_history(self):
        def get_portfolio_history(*_, **__):

            target_date = datetime.today() - timedelta(days=30)

            return [{
                'date': format_date_short(target_date),
                'components': [
                    {},
                    {},
                    {},
                    {
                        'ffill_used': False,
                        'fx_rate': None,
                        'isin': 'XF0000000EUR',
                        'name': 'Prospery Invest cash artificial account',
                        'price': 1,
                        'price_eur': 1,
                        'quantity': 0
                    }],
            }]

        with patch('pdf.utils.get_portfolio_history',
                   get_portfolio_history):
            report = self.generate_report()
            response = self.view_report(report.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class UsersRiskScoreTest(InternalReportBasicTest):

    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self, upper_risk_score=None, lower_risk_score=None):

        url = reverse('internal:generate-active-users-list')

        request = self.factory.get(url)
        request.user = self.service_c_user

        request.query_params = dict(
            upper_risk_score=upper_risk_score,
            lower_risk_score=lower_risk_score

        )
        view = GenerateUsersRiskScoreView()

        return view.generate_users_risk_score_list(request=request)

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClient.risk_profile_user)
    def test_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def generate_report(self, upper_risk_score=None, lower_risk_score=None):
        response = self.send_request(
            upper_risk_score=upper_risk_score,
            lower_risk_score=lower_risk_score
        )

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterRiskScoreUsersList(
            context=self.context,
            upper_risk_score=upper_risk_score,
            lower_risk_score=lower_risk_score
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClient.risk_profile_user)
    def test_generate_users_risk_score_list(self):
        report = self.generate_report(70)
        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClient.risk_profile_user)
    def test_generate_users_risk_score_list_without_limits(self):
        report = self.generate_report()
        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClient.risk_profile_user)
    def test_generate_users_risk_score_list_without_upper(self):
        self.risk_profile = RiskProfile.objects.create(
            value=10,
            upper_range=5,
            lower_range=-5,
            context=self.context
        )
        UserRiskProfile.objects.create(
            user=self.context.usermapping_set.first(),
            risk_profile=self.risk_profile
        )
        report = self.generate_report(None, 5)
        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClient.risk_profile_user)
    def test_generate_users_risk_score_list_without_lower(self):
        report = self.generate_report(70, None)
        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_users_risk_score_list_no_users(self):
        report = self.generate_report(1)

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report.id)

    def test_get_report_not_yet_existing(self):
        response = self.send_request(1)

        report_id = response.data['id']

        response = self.view_report(report_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report_id, file_format=FILE_FORMAT_JSON)

    @patch.object(CoreInteractClient, 'risk_profile_user',
                  MockCoreInteractClientEmptyResponse.risk_profile_user)
    def test_generate_users_risk_score_list_error(self):
        report = self.generate_report(100)
        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MockUserQuarterReportValidator(object):
    def validate(self):
        raise FakeError


class ValidateQuarterReportsDataTest(InternalReportBasicTest):

    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    @patch.object(ThreadPool, 'map', PoolWithoutThreads.map)
    def send_request(self, end_date=None):
        request = self.factory.get(reverse('internal:validate-quarter-data'))
        request.user = self.service_c_user

        request.query_params = dict()

        if end_date:
            request.query_params.update(dict(
                end_date=format_date_short(end_date)
            ))

        view = QuarterDataValidationView()

        return view.validate_quarter_data(request=request)

    @patch.object(ThreadPool, 'map', PoolWithoutThreads.map)
    def generate_report(self, end_date=None):

        response = self.send_request(end_date=end_date)

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterInvalidQuarterData(
            context=self.context,
            end_date=format_date_short(end_date)
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def do_rebalancing_zero_step(self):
        url = reverse('rebalancing_zero_step')
        request = self.factory.post(url)
        request.user = self.service_c_user
        request.query_params = dict(
            user=self.user_mapping.app_uid
        )
        view = RebalancingView(request=request)
        view.action = 'zero_step'

        return view.zero_step(request=request)

    def do_rebalancing_first_step(self, rebalance_id, approved):
        url = reverse('rebalancing_first_step')
        request = self.factory.post(url)
        request.user = self.service_c_user
        request.query_params = dict(
            rebalancing_id=rebalance_id,
            approved='true' if approved else 'false'
        )
        view = RebalancingView(request=request, format_kwarg=None)
        view.action = 'first_step'

        return view.first_step(request=request)

    @patch.object(service_cClient, 'get_session_id',
                  Mockservice_cClient.get_session_id)
    @patch.object(service_cClient, 'authorized_request',
                  Mockservice_cClient.authorized_request)
    @patch.object(service_cClient, 'order', Mockservice_cClient.order)
    @patch.object(CoreAnalyse2Client, 'get_data',
                  MockAnalyseClientCorrectRebalance.get_data)
    def init_rebalancing(self):
        self.do_rebalancing_zero_step()
        rebalancing_order = service_cRebalancingOrder.objects.last()

        self.do_rebalancing_first_step(rebalancing_order.id, True)

        self.execute_orders_command()

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_no_users(self):
        UserMapping.objects.all().delete()
        self.generate_report(end_date=datetime.now().date())

    @patch.object(GearmanClient, 'get_gearman_data',
                  MockAssetPerformanceRequest.gearman_response)
    def test_with_data(self):
        self.user_mapping.has_portfolio_history = True
        self.user_mapping.save()

        order = self.create_order(settings.KEY_BUY, 100, self.user_mapping)
        self.cancel_order(order.id)

        self.create_order(settings.KEY_BUY, 100, self.user_mapping)
        self.execute_orders(self.user_mapping)

        self.create_order(settings.KEY_SELL, 50, self.user_mapping)
        self.execute_orders(self.user_mapping)

        def get_portfolio_history(start_date, end_date, user_mapping):
            return get_portfolio_mock_history(
                start_date=start_date,
                end_date=end_date,
                user_mapping=user_mapping
            )

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            self.generate_report(end_date=datetime.now().date())

    @patch.object(PerformanceGeometricPortfolioClient, 'action',
                  MockAnalyseClientWithWarnings.analyse_response)
    def test_with_data_ca_warning(self):

        self.context.asset_performance = DATA_SOURCE_CORE_ANALYSE_2
        self.context.save()

        self.user_mapping.has_portfolio_history = True
        self.user_mapping.save()

        order = self.create_order(settings.KEY_BUY, 100, self.user_mapping)
        self.cancel_order(order.id)

        with patch('pdf.utils.get_portfolio_history',
                   get_portfolio_mock_history_warning):

            self.generate_report(end_date=datetime.now().date())

        self.context.asset_performance = DATA_SOURCE_GEARMAN
        self.context.save()

    @patch.object(GearmanClient, 'get_gearman_data',
                  MockAssetPerformanceRequest.gearman_response)
    def test_with_rebalancing(self):
        self.user_mapping.has_portfolio_history = True
        self.user_mapping.save()

        self.init_rebalancing()

        def get_portfolio_history(start_date, end_date, user_mapping):
            return get_portfolio_mock_history(
                start_date=start_date,
                end_date=end_date,
                user_mapping=user_mapping
            )

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            self.generate_report(end_date=datetime.now().date())

    @patch.object(GearmanClient, 'get_gearman_data',
                  MockAssetPerformanceRequest.gearman_response)
    def test_with_sell_all(self):
        self.user_mapping.has_portfolio_history = True
        self.user_mapping.save()

        self.context.sell_all_boundary = 10
        self.context.save()

        investments = self.user_mapping.get_container_investments()

        all_ptf_value = 0

        self.create_order(settings.KEY_SELL, 100, self.user_mapping)
        self.execute_orders(self.user_mapping)

        for asset in investments.has_assets.all():
            all_ptf_value += asset.value

        order_value = all_ptf_value - 5

        self.create_order(settings.KEY_SELL, order_value, self.user_mapping)
        self.execute_orders(self.user_mapping)

        def get_portfolio_history(start_date, end_date, user_mapping):
            return get_portfolio_mock_history(
                start_date=start_date,
                end_date=end_date,
                user_mapping=user_mapping,
                zero_quantity=True
            )

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            self.generate_report(end_date=datetime.now().date())

    @patch.object(GearmanClient, 'get_gearman_data',
                  MockAssetPerformanceRequest.gearman_response)
    def test_with_new_user(self):
        user = create_user(self.context, 'new_user')
        user.has_portfolio_history = True
        user.save()

        assign_risk_profile(user, 15)
        self.create_bank_connection(user)
        self.create_order(settings.KEY_BUY, 100, user)
        self.execute_orders(self.user_mapping)

        def get_portfolio_history(start_date, end_date, user_mapping):
            return get_portfolio_mock_history(
                start_date=start_date,
                end_date=end_date,
                user_mapping=user_mapping,
            )

        quarter_start = get_quarter_dates(datetime.now().date())[0] - timedelta(
            days=1)

        last_quarter_end = get_quarter_dates(quarter_start)[1]

        with patch('pdf.utils.get_portfolio_history', get_portfolio_history):
            self.generate_report(
                end_date=last_quarter_end
            )

    def test_with_blank_user(self):
        user = create_user(self.context, 'new_user')
        user.has_portfolio_history = True
        user.save()

        assign_risk_profile(user, 15)
        self.create_bank_connection(user)

        quarter_start = get_quarter_dates(datetime.now().date())[0] - timedelta(
            days=1)

        last_quarter_end = get_quarter_dates(quarter_start)[1]

        self.generate_report(
            end_date=last_quarter_end
        )

    def test_with_transactions_after_quarter(self):
        user = create_user(self.context, 'new_user')
        user.has_portfolio_history = True
        user.save()

        quarter_start = get_quarter_dates(datetime.now().date())[0] - timedelta(
            days=1)

        last_quarter_end = get_quarter_dates(quarter_start)[1]

        assign_risk_profile(user, 15)
        self.create_bank_connection(user)
        self.create_order(settings.KEY_BUY, 100, user)
        self.execute_orders(self.user_mapping)

        self.generate_report(
            end_date=last_quarter_end
        )


class InternalReportGoalsTest(InternalReportBasicTest):
    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self, start_date=None, end_date=None):
        request = self.factory.get(reverse('internal:report-goals'))
        request.user = self.service_c_user

        request.query_params = dict(
            start_date=start_date,
            end_date=end_date
        )

        view = GoalsReportView()

        return view.get_goals_report(request=request)

    def generate_report(self, start_date=None, end_date=None):
        response = self.send_request(
            start_date=start_date,
            end_date=end_date
        )

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterGoals(
            context=self.context,
            start_date=start_date,
            end_date=end_date
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_generate_no_goals_report(self):
        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        report.refresh_from_db()
        report.status = INTERNAL_REPORT_STATUS_READY
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        with self.assertRaises(WrongFileFormat):
            self.download_report(report.id, file_format='fake')

        report.refresh_from_db()
        report.data = None
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

    def test_generate_goals_report(self):

        create_goal(self.user_mapping)

        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_goals_report_with_start_date_only(self):

        create_goal(self.user_mapping)

        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=50)))

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_goals_report_with_end_date_only(self):

        create_goal(self.user_mapping)

        report = self.generate_report(None, format_date_short(datetime.today()))

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_goals_report_with_both_dates(self):

        create_goal(self.user_mapping)

        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=5)),
            format_date_short(datetime.today()))

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InternalReportRecurrentOrdersTest(InternalReportBasicTest):
    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self, start_date=None, end_date=None,
                     direct_debit=None, period_finished=None):
        request = self.factory.get(
            reverse('internal:generate-recurrent-orders'))
        request.user = self.service_c_user

        request.query_params = dict(
            start_date=start_date,
            end_date=end_date,
            direct_debit=direct_debit,
            period_finished=period_finished
        )

        view = GenerateRecurrentOrdersView()

        return view.generate_recurrent_orders(request=request)

    def generate_report(self, start_date=None, end_date=None,
                     direct_debit=None, period_finished=None):
        response = self.send_request(
            start_date=start_date,
            end_date=end_date,
            direct_debit=direct_debit,
            period_finished=period_finished
        )

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterRecurrentOrders(
            context=self.context,
            start_date=start_date,
            end_date=end_date,
            direct_debit=direct_debit,
            period_finished=period_finished
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def create_recurrent_order(self):
        return RecurrentOrderContainer.objects.create(
            status=get_order_status(STATUS_ONGOING),
            frequency_type=RecurrentOrderContainer.DAILY,
            frequency=0,
            order_start_date=date.today() - timedelta(days=100),
            order_next_date=date.today() - timedelta(days=70),
            order_end_date=date.today() - timedelta(days=70),
            period_finished=True,
            direct_debit=True,
            amount=100,
            action=KEY_SELL,
            user=self.user_mapping,
            orders_created=0
        )

    def create_recurrent_order_false_params(self):
        return RecurrentOrderContainer.objects.create(
            status=get_order_status(STATUS_ONGOING),
            frequency_type=RecurrentOrderContainer.DAILY,
            frequency=0,
            order_start_date=date.today() - timedelta(days=100),
            order_next_date=date.today() - timedelta(days=70),
            order_end_date=date.today() - timedelta(days=70),
            period_finished=False,
            direct_debit=False,
            amount=100,
            action=KEY_SELL,
            user=self.user_mapping,
            orders_created=0
        )

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_generate_no_recurrent_orders_report(self):
        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        report.refresh_from_db()
        report.status = INTERNAL_REPORT_STATUS_READY
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        with self.assertRaises(WrongFileFormat):
            self.download_report(report.id, file_format='fake')

        report.refresh_from_db()
        report.data = None
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

    def test_generate_recurrent_orders_report(self):
        self.create_recurrent_order()

        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_recurrent_orders_report_with_date_range_only(self):
        self.create_recurrent_order()

        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=5)),
            format_date_short(datetime.today())
        )

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_recurrent_orders_report_with_params_true(self):
        self.create_recurrent_order()

        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=5)),
            format_date_short(datetime.today()),
            'True',
            'True'
        )

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_recurrent_orders_report_with_params_false(self):
        self.create_recurrent_order_false_params()

        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=5)),
            format_date_short(datetime.today()),
            'False',
            'False'
        )

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_recurrent_orders_report_with_params_wrong(self):
        self.create_recurrent_order_false_params()

        with self.assertRaises(WrongInputValue):
            self.generate_report(
                format_date_short(datetime.today() - timedelta(days=5)),
                format_date_short(datetime.today()),
                'False',
                'wrong'
            )


class InternalReportOrdersTest(InternalReportBasicTest):
    def setUp(self):
        super(InternalReportOrdersTest, self).setUp()

        self.order = Order.objects.create(
            action='BUYI',
            status=STATUS_PENDING,
            user=self.user_mapping,
            amount=100,
            value_date=datetime.today()
        )

    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self, start_date=None, end_date=None):
        request = self.factory.get(
            reverse('internal:generate-orders'))
        request.user = self.service_c_user

        request.query_params = dict(
            start_date=start_date,
            end_date=end_date
        )

        view = GenerateOrdersView()

        return view.generate_orders(request=request)

    def generate_report(self, start_date=None, end_date=None):
        response = self.send_request(
            start_date=start_date,
            end_date=end_date
        )

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterOrders(
            context=self.context,
            start_date=start_date,
            end_date=end_date,
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_generate_no_orders_report(self):
        report = self.generate_report(
            format_date_short(datetime.today() + timedelta(days=5)),
            format_date_short(datetime.today() + timedelta(days=10))
        )

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        report.refresh_from_db()
        report.status = INTERNAL_REPORT_STATUS_READY
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        with self.assertRaises(WrongFileFormat):
            self.download_report(report.id, file_format='fake')

        report.refresh_from_db()
        report.data = None
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

    def test_generate_orders_report(self):
        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_orders_report_with_date_range(self):
        report = self.generate_report(
            format_date_short(datetime.today() - timedelta(days=5)),
            format_date_short(datetime.today())
        )

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InternalBalancesTest(InternalReportBasicTest):
    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self):
        request = self.factory.get(
            reverse('internal:generate-balances'))
        request.user = self.service_c_user

        view = GenerateBalancesView()

        return view.generate_balances(request=request)

    def generate_report(self):
        response = self.send_request()

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterBalances(
            context=self.context
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def generate_report_fake_context(self):
        response = self.send_request()

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        context = AppContext.objects.create(
            id=999,
            name='fake_context',
            recurrent_orders_max_retry=2
        )

        generator = ReporterBalances(
            context=context
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_generate_no_balances_report(self):
        report = self.generate_report_fake_context()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(CanNotDownloadReportError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        report.refresh_from_db()
        report.status = INTERNAL_REPORT_STATUS_READY
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

        with self.assertRaises(WrongFileFormat):
            self.download_report(report.id, file_format='fake')

        report.refresh_from_db()
        report.data = None
        report.save()

        with self.assertRaises(ReportDataError):
            self.download_report(report.id, file_format=FILE_FORMAT_JSON)

    def test_generate_orders_report(self):
        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_no_report_data(self):
        report = self.generate_report_fake_context()
        report.data = None
        report.save()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InternalReportListTest(InternalReportBasicTest):
    def send_request(self,
                     start_date=None,
                     end_date=None,
                     report_type=None,
                     report_status=None):

        request = self.factory.get(reverse('internal:list'))
        request.user = self.service_c_user

        request.query_params = dict()

        if start_date:
            request.query_params.update(start_date=start_date)

        if end_date:
            request.query_params.update(end_date=end_date)

        if report_type:
            request.query_params.update(type=report_type)

        if report_status:
            request.query_params.update(status=report_status)

        view = GetReportsListView()

        return view.get_all(request=request)

    def test_check_endpoint_dates_in_future(self):

        date = format_date_short(datetime.now().date() + timedelta(days=100))

        with self.assertRaises(WrongParameterError):
            self.send_request(
                start_date=date,
                end_date=date
            )

    def test_check_endpoint_wrong_dates_order(self):

        start_date = format_date_short(datetime.now().date())

        end_date = format_date_short(datetime.now().date() - timedelta(days=10))

        with self.assertRaises(WrongParameterError):
            self.send_request(
                start_date=start_date,
                end_date=end_date
            )

    def test_check_endpoint_no_dates(self):

        response = self.send_request()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_check_endpoint_correct_dates(self):

        date = format_date_short(datetime.now().date())

        response = self.send_request(
            start_date=date,
            end_date=date
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_check_endpoint_broken_report(self):

        InternalReport.objects.create(
            context=self.context,
            type=INTERNAL_REPORT_ACTIVE_USERS,
            status=INTERNAL_REPORT_STATUS_GENERATING,
            input_data=json.dumps({}),
            generated=datetime.now() - timedelta(hours=48)
        )
        start_date = format_date_short(
            datetime.now().date() - timedelta(hours=72))
        end_date = format_date_short(datetime.now().date())

        response = self.send_request(
            start_date=start_date,
            end_date=end_date
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InternalReportAssetsList(InternalReportBasicTest):
    @patch('internal_reports.generator.generate_report_in_background.delay',
           generate_report_in_background)
    def send_request(self):
        request = self.factory.get(reverse('internal:generate-assets-list'))
        request.user = self.service_c_user

        request.query_params = dict()

        view = GenerateAssetsView()

        return view.generate_assets_list(request=request)

    def generate_report(self):
        response = self.send_request( )

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        generator = ReporterAssets(
            context=self.context
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def generate_report_fake_context(self):
        response = self.send_request()

        report_id = response.data['id']

        internal_report = InternalReport.objects.get(pk=report_id)

        context = AppContext.objects.create(
            id=9999,
            name='fake_context_without_assets',
            recurrent_orders_max_retry=2
        )

        generator = ReporterAssets(
            context=context
        )

        generator.internal_report = internal_report

        generator.run(internal_report)

        internal_report.refresh_from_db()

        return internal_report

    def test_check_endpoint(self):
        response = self.send_request()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_generate_orders_report(self):
        report = self.generate_report()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.download_report(report.id, file_format=FILE_FORMAT_JSON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_no_report_data(self):
        report = self.generate_report_fake_context()
        report.data = None
        report.save()

        response = self.view_report(report.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
