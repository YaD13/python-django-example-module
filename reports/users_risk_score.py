import json
from datetime import datetime

from datastorage.models import UserRiskProfile
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_FAILED,
    INTERNAL_REPORT_STATUS_READY
)
from pdf.errors import ReportWasNotGenerated
from pdf.generators.utils import get_risk_profile
from tools.dates import format_date_long


class ReporterRiskScoreUsersList:
    """
    Prepare users list with risk score lower then desired_risk_score
    """
    def __init__(self, context, lower_risk_score, upper_risk_score):
        """
        Initialise reporter
        :param context: AppContext instance
        :param lower_risk_score: value to filter users
        :param upper_risk_score: value to filter users
        """

        self.upper_risk_score = upper_risk_score
        self.lower_risk_score = lower_risk_score
        self.context = context
        self.users_risk_score_list = list()

        self.internal_report = None

    def run(self, internal_report):
        """
        Generate actual report
        :param internal_report: Internal report instance
        """

        user_risk_profile_qs = UserRiskProfile.objects.filter(
            user__app_context=self.context
        )

        self.internal_report = internal_report

        if self.upper_risk_score:
            user_risk_profile_qs = user_risk_profile_qs.filter(
                risk_profile__value__lt=self.upper_risk_score)

        if self.lower_risk_score:
            user_risk_profile_qs = user_risk_profile_qs.filter(
                risk_profile__value__gt=self.lower_risk_score)

        if not len(user_risk_profile_qs):
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = ('There is no users with risk score '
                                         'in these limits')
            self.internal_report.save()
            return

        self.prepare_user_data(user_risk_profile_qs)

        self.internal_report.data = json.dumps(self.users_risk_score_list,
                                               indent=4)
        self.internal_report.generated = datetime.now()
        self.internal_report.status = INTERNAL_REPORT_STATUS_READY
        self.internal_report.save()

    def prepare_user_data(self, user_risk_profile_qs):
        """
        Prepare data for single user
        :param user_risk_profile_qs: UserRiskProfile queryset
        """

        for user_risk_profile in user_risk_profile_qs:
            user = user_risk_profile.user
            portfolio_value = 0
            container = user.get_container_investments()

            if container:
                portfolio_value = container.get_value()

            suggested_score = self.__get_suggested_risk_score(user_risk_profile)

            self.users_risk_score_list.append(dict(
                user_id=user.app_uid,
                selected_user_risk_score=user_risk_profile.risk_profile.value,
                suggested_user_risk_score=suggested_score,
                risk_score_date_save=format_date_long(
                    user_risk_profile.last_modified),
                investments_portfolio_value=portfolio_value
            ))

    @staticmethod
    def __get_suggested_risk_score(user_risk_profile):
        """
        Get suggested risk score
        :param user_risk_profile:
        :return: suggested risk score
        """
        try:
            return get_risk_profile(user_risk_profile.user)['risk_profile'][
                'value']
        except ReportWasNotGenerated:
            return user_risk_profile.risk_profile.value
