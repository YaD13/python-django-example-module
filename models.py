import json
from datetime import datetime

from django.db import models

from internal_reports.constants import (
    INTERNAL_REPORT_TYPES,
    INTERNAL_REPORT_STATUSES,
    INTERNAL_REPORT_CSV_COLUMNS)
from permission.models import AppContext


class InternalReport(models.Model):
    """
    Table to store internal reports.

    :cvar context: AppContext this report related to
    :cvar type: report type
    :cvar status: report status
    :cvar generated: timestamp when report was generated
    :cvar input_data: info from report request
    :cvar data: report data
    """

    context = models.ForeignKey(AppContext, verbose_name="Context")
    type = models.SmallIntegerField(choices=INTERNAL_REPORT_TYPES)
    status = models.SmallIntegerField(choices=INTERNAL_REPORT_STATUSES)
    generated = models.DateTimeField(default=datetime.now)
    input_data = models.TextField()
    data = models.TextField(null=True, blank=True)

    def __str__(self):
        return '{type} report ({status}) from {date}'.format(
            type=self.get_type_display(),
            status=self.get_status_display(),
            date=self.generated
        )

    def get_csv_columns(self):
        return INTERNAL_REPORT_CSV_COLUMNS[self.type]

    def get_data(self):
        if not self.data:
            return 'Report has no data'
        else:
            try:
                return json.loads(self.data)
            except ValueError:
                return 'Report has broken data'
