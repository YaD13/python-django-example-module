import json
from datetime import datetime

from datastorage.models import Order, AssetContainer
from internal_reports.constants import (
    INTERNAL_REPORT_STATUS_READY,
    INTERNAL_REPORT_STATUS_FAILED
)


class ReporterBalances:
    """
    Reporter for balances
    """
    def __init__(self, context):
        """
        Initialise balances reporter
        :param context: AppContext instance
        """

        self.context = context
        self.data = list()
        self.internal_report = None

    def run(self, internal_report):
        """
        Generate report with balances
        """

        asset_containers = AssetContainer.objects.filter(
            user__app_context=self.context)

        self.internal_report = internal_report

        self.prepare_asset_containers_data(asset_containers)

        if self.data:
            self.data = sorted(self.data, key=lambda k: k['user_id'])
            self.internal_report.data = json.dumps(self.data,
                                                   indent=4)
            self.internal_report.status = INTERNAL_REPORT_STATUS_READY
            self.internal_report.generated = datetime.now()

        else:
            self.internal_report.status = INTERNAL_REPORT_STATUS_FAILED
            self.internal_report.data = 'No users with order'

        self.internal_report.save()

    def prepare_asset_containers_data(self, asset_containers):
        """
        Generate report entry for user

        :param asset_containers: AssetContainers queryset
        """

        for asset_container in asset_containers:
            self.data.append(dict(
                user_id=asset_container.user.app_uid,
                name=asset_container.name,
                type=asset_container.type.name,
                total_value=asset_container.get_value()
            )
            )
