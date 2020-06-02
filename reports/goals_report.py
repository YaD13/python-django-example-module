import json
from datetime import datetime

from datastorage.models import Goal
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)
from internal_reports.utils import (
    filter_queryset_by_date_range,
    format_date_short_or_none
)
from tools.dates import format_date_long, read_date_short


class ReporterGoals:
    """
    Reporter for users goals
    """
    def __init__(self, context, start_date, end_date):
        """
        Initialise goals reporter

        :param context: AppContext instance
        :param start_date: string date for filtering goals
        :param end_date: string date for filtering goals
        """

        self.context = context
        self.start_date = read_date_short(start_date) if start_date else None
        self.end_date = read_date_short(end_date) if end_date else None
        self.data = list()
        self.internal_report = None

    def run(self, internal_report):
        """
        Generate report with users goals count

        :param internal_report: Internal report instance
        """

        goals = Goal.objects.filter(user__app_context=self.context)

        self.internal_report = internal_report

        goals = filter_queryset_by_date_range(
            goals, self.start_date, self.end_date, 'created')

        self.prepare_goals_data(goals)

        if self.data:
            self.data = sorted(self.data, key=lambda k: k['user_id'])
            self.internal_report.data = json.dumps(self.data,
                                                   indent=4)
            self.internal_report.status = INTERNAL_REPORT_STATUS_READY
            self.internal_report.generated = datetime.now()

        else:
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = 'No users with goals'

        self.internal_report.save()

    def prepare_goals_data(self, goals):
        """
        Generate report entry for user

        :param goals: Goals queryset
        """

        for goal in goals:
            self.data.append(dict(
                user_id=goal.user.app_uid,
                goal_id=goal.id,
                type=goal.type.name,
                value=goal.value,
                created=format_date_long(goal.created),
                start_date=format_date_short_or_none(goal.start_date),
                end_date=format_date_short_or_none(goal.end_date),
                frequency=goal.frequency,
            )
            )
