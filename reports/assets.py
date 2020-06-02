import json
from datetime import datetime

from datastorage.models import Asset
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)
from internal_reports.serializers import InternalReportAssetsSerializer


class ReporterAssets:
    """
    Reporter for assets
    """
    def __init__(self, context):
        """
        Initialise assets reporter
        :param context: AppContext instance
        """

        self.context = context
        self.internal_report = None

    def run(self, internal_report):
        """
        Generate report with assets
        """

        self.internal_report = internal_report

        assets = Asset.objects.filter(user__app_context=self.context)

        if assets:
            assets = InternalReportAssetsSerializer(assets, many=True).data
            assets = sorted(assets, key=lambda k: k['user_id'])
            self.internal_report.data = json.dumps(assets, indent=4)
            self.internal_report.status = INTERNAL_REPORT_STATUS_READY
            self.internal_report.generated = datetime.now()

        else:
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = 'No assets'

        self.internal_report.save()
