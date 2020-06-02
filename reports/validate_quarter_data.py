import json
import logging
from datetime import datetime
from multiprocessing.dummy import Pool

from common.decorators import log_time_ranges
from datastorage.models import Transaction
from historicals.utils import get_quarter_dates
from internal_reports.constants import INTERNAL_REPORT_STATUS_READY
from internal_reports.errors import TransactionsOutOfQuarterError
from pdf.generators.quarter_report_modules.overview import (
    get_portfolio_overview
)
from pdf.generators.quarter_report_modules.performance import (
    PortfolioPerformanceGenerator
)
from pdf.generators.quarter_report_modules.summary import (
    PortfolioSummaryCalculator
)
from pdf.utils import (
    get_formatted_portfolio_history,
    get_portfolio_creating_date
)
from permission.models import UserMapping
from serviceAPI.settings import ISIN_CASH_COMPONENT
from tools.dates import format_date_short, read_date_short
from datastorage.constants import TRANSACTION_TYPE_BUY


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MESSAGE_STARTED = 'User {} check started'
MESSAGE_FINISHED = 'User {} check finished'
MESSAGE_FAILED = 'User {} check failed'
MESSAGE_FAILED_NO_DATA = 'User {} check failed (No data to check)'
MESSAGE_ALL_VALID_DATA = 'All users have valid data for requested quarter'


class ReporterInvalidQuarterData:
    """
    Validator class for Quarter reports
    """

    def __init__(self, end_date, context):
        """
        Initialise quarter reports validator

        :param end_date: quarter end date
        :param context: AppContext instance
        """
        end_date_obj = read_date_short(end_date).date()
        start_date = get_quarter_dates(end_date_obj)[0]

        self.start_date = start_date
        self.end_date = end_date_obj
        self.context = context
        self.data = list()

        self.internal_report = None

    @log_time_ranges
    def run(self, internal_report):
        """
        Validate all users quarter reports
        :param internal_report: Internal report instance

        :return: Response with invalid data
        """

        user_mappings = UserMapping.objects.filter(
            app_context=self.context,
            has_portfolio_history=True,
        )

        self.internal_report = internal_report

        pool = Pool(self.context.threads_core_analyse_2)
        pool.map(self.handle_user, user_mappings)
        pool.close()
        pool.join()

        self.internal_report.status = INTERNAL_REPORT_STATUS_READY

        if self.data:
            self.internal_report.data = json.dumps(self.data,
                                                   indent=4)
            self.internal_report.generated = datetime.now()
        else:
            self.internal_report.data = MESSAGE_ALL_VALID_DATA

        self.internal_report.save()

    def handle_user(self, user_mapping):
        """
        Validate data for certain user

        :param user_mapping: UserMapping instance
        """

        logger.info(MESSAGE_STARTED.format(user_mapping))

        try:
            data = UserQuarterDataValidator(
                user_mapping=user_mapping,
                start_date=self.start_date,
                end_date=self.end_date
            ).validate()

            if data:
                self.data.append(data)

            logger.info(MESSAGE_FINISHED.format(user_mapping))

        except TransactionsOutOfQuarterError:
            logger.info(MESSAGE_FAILED_NO_DATA.format(user_mapping))

        except Exception as ex:
            self.data.append(
                dict(
                    user_id=user_mapping.app_uid,
                    error=str(ex)
                )
            )

            logger.info(MESSAGE_FAILED.format(user_mapping))


class UserQuarterDataValidator:
    """
    User quarter report validator
    """
    def __init__(self, user_mapping, start_date, end_date):
        """
        Initialise user's quarter report data
        :param user_mapping: UserMapping instance
        :param start_date: quarter start date
        :param end_date: quarter end date
        """

        self.user_mapping = user_mapping
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio_creating_date = get_portfolio_creating_date(
            user_mapping=user_mapping,
            start_date=start_date
        )

        self.revenue_per_asset_valid = False
        self.vs_valid = False
        self.revenue_is_valid = False
        self.start_valid = False
        self.end_valid = False
        self.trans_and_revenue_valid = False

        self.summary = None
        self.overview = None

    def prepare_data(self):
        """
        Prepare quarter report data that will be validated
        """

        transactions = Transaction.objects.filter(
            user=self.user_mapping,
            type=TRANSACTION_TYPE_BUY
        )

        if not transactions.exists():
            raise TransactionsOutOfQuarterError

        history = get_formatted_portfolio_history(
            user_mapping=self.user_mapping,
            portfolio_creating_date=self.portfolio_creating_date,
            end_date=self.end_date
        )

        portfolio_performance = PortfolioPerformanceGenerator(
            user_mapping=self.user_mapping,
            start_date=self.start_date,
            end_date=self.end_date,
            portfolio_creating_date=self.portfolio_creating_date
        ).get_performance_data()

        self.summary = PortfolioSummaryCalculator(
            user_mapping=self.user_mapping,
            start_date=self.start_date,
            end_date=self.end_date,
            portfolio_creating_date=self.portfolio_creating_date,
            portfolio_history=history,
            costs=None,
            portfolio_performance=portfolio_performance
        ).calculate_extended()

        date = self.end_date

        last_sell_date = self.summary['last_sell_date']

        if last_sell_date:
            date = last_sell_date

        self.overview = get_portfolio_overview(
            start_date=self.start_date,
            end_date=date,
            portfolio_creating_date=self.portfolio_creating_date,
            portfolio_history=history
        )['data']

    def validate(self):
        """
        Validate quarter report data
        :return: dict of invalid data
        """

        if self.portfolio_creating_date > self.end_date:
            return

        self.prepare_data()

        if not self.is_report_data_valid():
            self.summary.pop('flow_per_asset')

            last_sell_date = self.summary['last_sell_date']

            if last_sell_date:
                last_sell_date = format_date_short(last_sell_date)
                self.summary['last_sell_date'] = last_sell_date

            return dict(
                user_id=self.user_mapping.app_uid,
                start_date=format_date_short(self.start_date),
                end_date=format_date_short(self.end_date),
                context=self.user_mapping.app_context.name,
                revenue_is_valid=self.revenue_is_valid,
                start_values_are_valid=self.start_valid,
                end_values_are_valid=self.end_valid,
                transaction_and_revenue_valid=self.trans_and_revenue_valid,
                is_cash_component_valid=self.vs_valid,
                revenue_per_asset_valid=self.revenue_per_asset_valid,
                **self.summary
            )

    def is_report_data_valid(self):
        """
        Check if quarter report data is valid
        :return: boolean value that shows if data valid
        """

        self.validate_revenue_per_asset(self.summary, self.overview)
        self.validate_revenue(self.summary)
        self.validate_portfolio_values(self.summary, self.overview)

        return (self.revenue_per_asset_valid
                and self.vs_valid
                and self.revenue_is_valid
                and self.start_valid
                and self.end_valid
                and self.trans_and_revenue_valid)

    def validate_revenue_per_asset(self, summary, overview_raw):
        """
        Validate revenue value using data from each asset
        :param summary: Quarter summary data
        :param overview_raw: Quarter overview data
        """

        assets_balance = 0

        isins = list()

        overview = dict()

        for item in overview_raw:
            isins.append(item['isin'])
            overview[item['isin']] = item

        asset_values = dict()
        assets_data = dict()

        vs_flow = summary['flow_per_asset'][ISIN_CASH_COMPONENT]

        isins += summary['flow_per_asset'].keys()

        for isin in set(isins):

            start_value = overview.get(isin, dict()).get('start_total_value', 0)
            end_value = overview.get(isin, dict()).get('end_total_value', 0)
            flow_value = summary['flow_per_asset'].get(isin, 0)

            asset_values[isin] = dict(
                start_value=start_value,
                end_value=end_value
            )

            assets_balance += start_value + flow_value - end_value

            assets_data[isin] = dict(
                start_value=round(start_value, 2),
                flow=flow_value,
                end_value=round(end_value, 2),
                asset_return=round(end_value - flow_value - start_value, 2)
            )

        revenue_per_asset = round(round(assets_balance, 2)
                                  + round(summary['return_in_cash'], 2), 2)

        self.revenue_per_asset_valid = revenue_per_asset == 0

        self.vs_valid = (
                round(asset_values[ISIN_CASH_COMPONENT]['end_value'], 2)
                == round(vs_flow
                         + asset_values[ISIN_CASH_COMPONENT]['start_value'], 2))

    def validate_revenue(self, summary_data):
        """
        Validate if revenue or loss less than 10 percents
        :param summary_data: portfolio summary data
        :return: boolean value which shows if revenue or loss less than 10%
        """
        revenue_in_percents = summary_data['cumulative_performance']

        self.revenue_is_valid = -0.1 <= revenue_in_percents <= 0.1

    def validate_portfolio_values(self, summary, overview):
        """
        Validate if values for start and end of the quarter are correct
        :param summary: Quarter summary data
        :param overview: Quarter overview data
        """

        overview_start = 0
        overview_end = 0

        if summary['flow_before_last_sell'] is not None:
            flow = round(summary['flow_before_last_sell'], 2)
        else:
            flow = round(summary['net_inflow_outflow'], 2)

        ptf_end = round(summary['ptf_before_last_sell']
                        or summary['portfolio_end_value'], 2)

        for item in overview:
            overview_start += item['start_total_value']
            overview_end += item['end_total_value']

        self.start_valid = (round(overview_start, 2)
                            == round(summary['portfolio_start_value'], 2))
        self.end_valid = round(overview_end, 2) == ptf_end

        self.trans_and_revenue_valid = (
                round(summary['portfolio_start_value']
                      + flow + summary['return_in_cash'], 2)
                == ptf_end)
