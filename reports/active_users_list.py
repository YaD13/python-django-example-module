import json
from datetime import datetime

from client_core_analyse.errors import CanNotConnectToCoreAnalyze
from datastorage.standards import ASSET_CONTAINER_TYPES
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)
from internal_reports.errors import BrokenPortfolioComponent
from pdf.errors import NoPortfolioHistory
from pdf.utils import get_formatted_portfolio_history
from permission.models import UserMapping
from serviceAPI import settings
from tools.dates import format_date_short, read_date_short


class ReporterActiveUsersList:
    """
    Reporter that generate list of active users with requested parameters
    """

    def __init__(self, start_date, end_date, consecutive_days,
                 amount_to_validate, context):
        """
        Initialise reporter

        :param start_date: Period start date
        :param end_date: Period end date
        :param consecutive_days: Number of consecutive days
        :param amount_to_validate: Min value of portfolio that user should have
        :param context: AppContext instance
        """

        self.start_date = read_date_short(start_date) if start_date else None
        self.end_date = read_date_short(end_date) if start_date else None
        self.consecutive_days = consecutive_days
        self.amount_to_validate = amount_to_validate
        self.context = context

        self.active_users_list = list()

        self.internal_report = None

    def run(self, internal_report):
        """
        Trigger report generating
        :param internal_report: Internal report instance

        :return: list with data
        """

        users = get_users_with_investments(self.context)

        self.internal_report = internal_report

        self.prepare_user_data(users)

        self.internal_report.data = json.dumps(self.active_users_list,
                                               indent=4)
        self.internal_report.status = INTERNAL_REPORT_STATUS_READY
        self.internal_report.generated = datetime.now()

        if not len(self.active_users_list):
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = (
                'There were no active users in the period')

        self.internal_report.save()

    def prepare_user_data(self, users):
        """
        Prepare data for certain user
        :param users: UserMapping queryset
        """
        for user in users:
            try:
                portfolio_history = get_formatted_portfolio_history(
                    user, self.start_date, self.end_date)
                portfolio_history_dates = list(portfolio_history.keys())
                (
                    consecutive_days_data,
                    average_value_of_consecutive_days
                ) = DailyPortfolioValue().check_daily_portfolio_value(
                    portfolio_history, self.consecutive_days,
                    self.amount_to_validate)

                if len(consecutive_days_data):
                    average_portfolio_value = calc_average_portfolio_value(
                        portfolio_history)

                    self.active_users_list.append(prepare_active_user_data(
                        average_portfolio_value,
                        portfolio_history,
                        portfolio_history_dates,
                        user,
                        consecutive_days_data,
                        average_value_of_consecutive_days
                    ))
            except (NoPortfolioHistory,
                    BrokenPortfolioComponent,
                    CanNotConnectToCoreAnalyze) as ex:
                self.active_users_list.append(prepare_failed_user_data(user, ex))


def get_users_with_investments(context):
    """
    Get users with investments
    :param context: AppContext instance

    :return: queryset
    """

    return UserMapping.objects.filter(
        app_context=context,
        assetcontainer__type__type_id=ASSET_CONTAINER_TYPES['depot']['code'],
        assetcontainer__source__is_prospery=True,
        order__isnull=False,
        order__action=settings.BUY,
        has_portfolio_history=True
    ).distinct()


def prepare_active_user_data(average_portfolio_value,
                             portfolio_history,
                             portfolio_history_dates,
                             user,
                             consecutive_days_data,
                             average_value_of_consecutive_days):
    """
    Prepare dict with data for each user
    :param average_portfolio_value: average portfolio value for current user
    :param portfolio_history: portfolio history
    :param portfolio_history_dates: list with dates from portfolio history
    :param user: user object
    :param consecutive_days_data: list with consecutive days data consist of
        date and daily_portfolio_value for each day
    :param average_value_of_consecutive_days:
    :return:
    """
    return dict(
        personid=user.app_uid,
        position_start_date=format_date_short(consecutive_days_data[0]['date']),
        position_start_value=round(
            consecutive_days_data[0]['daily_portfolio_value'], 2),
        position_average_value=round(average_portfolio_value, 2),
        position_end_date=format_date_short(portfolio_history_dates[-1]),
        position_end_value=calc_daily_portfolio_value(
            portfolio_history.get(portfolio_history_dates[-1])['components']),
        consecutive_days=len(consecutive_days_data),
        average_value_of_consecutive_days=round(
            average_value_of_consecutive_days, 2),
        first_date_reported=format_date_short(portfolio_history_dates[0]),
        position_first_date_reported=calc_daily_portfolio_value(
            portfolio_history.get(portfolio_history_dates[0])['components']),
        error=None
    )


def prepare_failed_user_data(user, error):
    """
    Prepare dict with data for failed user
    :param user: user object
    :param error: error that happened for user
    :return:
    """
    return dict(
        personid=user.app_uid,
        position_start_date='',
        position_start_value='',
        position_average_value='',
        position_end_date='',
        position_end_value='',
        consecutive_days='',
        average_value_of_consecutive_days='',
        first_date_reported='',
        position_first_date_reported='',
        error=str(error)
    )


class DailyPortfolioValue:
    def __init__(self):
        self.consecutive_days_data = list()
        self.total_value_consecutive_days = 0

    def check_daily_portfolio_value(self,
                                    portfolio_history,
                                    expected_consecutive_days,
                                    amount_to_validate):
        """
        Check daily portfolio value to be equal or higher then
        amount_to_validate
        :param portfolio_history: portfolio history
        :param expected_consecutive_days:
        :param amount_to_validate: value to validate user's investment
        :return: list of consecutive_days_data and average consecutive days
            portfolio value
        """

        for key, value in portfolio_history.items():
            daily_ptf_value = calc_daily_portfolio_value(value['components'])

            if daily_ptf_value >= amount_to_validate:
                self.consecutive_days_data.append(
                    dict(date=key,
                         daily_portfolio_value=daily_ptf_value)
                )
                self.total_value_consecutive_days += daily_ptf_value

            elif len(self.consecutive_days_data) >= expected_consecutive_days:
                break
            else:
                self.consecutive_days_data = list()
                self.total_value_consecutive_days = 0

        return self.calc_average_value_of_consecutive_days(
            expected_consecutive_days)

    def calc_average_value_of_consecutive_days(self, expected_consecutive_days):
        """
        Calc average value of consecutive days
        :param expected_consecutive_days:
        :return: consecutive days data and average value of consecutive days
        """
        if len(self.consecutive_days_data) >= expected_consecutive_days:
            return (self.consecutive_days_data,
                    self.total_value_consecutive_days /
                    len(self.consecutive_days_data))
        return list(), 0


def calc_average_portfolio_value(portfolio_history):
    """
    Calculate average portfolio value
    :param portfolio_history: portfolio history
    :return: average portfolio value
    """
    total_portfolio_value = 0
    for key, value in portfolio_history.items():
        total_portfolio_value += calc_daily_portfolio_value(value['components'])

    return total_portfolio_value / len(portfolio_history)


def calc_daily_portfolio_value(components):
    """
    Calculate portfolio value for current day
    :param components: portfolio component
    :return: daily portfolio value
    """
    daily_portfolio_value = 0
    for component in components:
        try:
            daily_portfolio_value += (component['price_eur']
                                      * component['quantity'])
        except KeyError:
            raise BrokenPortfolioComponent
    return round(daily_portfolio_value, 2)
