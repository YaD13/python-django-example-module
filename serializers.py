import json
from datetime import date, datetime

from django.core.exceptions import ValidationError
from rest_framework import serializers

from datastorage.models import Asset
from internal_reports.constants import (
    INTERNAL_REPORT_TYPES,
    INTERNAL_REPORT_STATUSES
)
from internal_reports.models import InternalReport
from internal_reports.utils import format_date_short_or_none
from tools.utils import BasicDataSerializer
from tools.dates import (
    format_date_long,
    DATE_FORMAT_SHORT
)


class InternalReportSerializer(serializers.ModelSerializer):
    """
    Serializer for list of internal reports
    """

    class Meta:
        model = InternalReport
        fields = ('id', 'context', 'type', 'status', 'generated', 'input_data')

    context = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    generated = serializers.SerializerMethodField()
    input_data = serializers.SerializerMethodField()

    @staticmethod
    def get_context(obj):
        return obj.context.name

    @staticmethod
    def get_type(obj):
        return dict(
            name='{} report'.format(obj.get_type_display()),
            code=obj.type
        )

    @staticmethod
    def get_status(obj):
        return dict(
            name=obj.get_status_display(),
            code=obj.status
        )

    @staticmethod
    def get_generated(obj):
        return format_date_long(obj.generated)

    @staticmethod
    def get_input_data(obj):
        return json.loads(obj.input_data)


class InternalReportDetailedSerializer(InternalReportSerializer):
    """
    Serializer for single internal report
    """

    data = serializers.SerializerMethodField()

    class Meta:
        model = InternalReport
        fields = ('id', 'context', 'type', 'status', 'generated', 'input_data',
                  'data')

    @staticmethod
    def get_data(obj):
        if not obj.data:
            return {}
        try:
            return json.loads(obj.data)
        except ValueError:
            return obj.data


class InternalReportListRequestSerializer(BasicDataSerializer):
    start_date = serializers.DateField(
        input_formats=[DATE_FORMAT_SHORT, ],
        required=False
    )
    end_date = serializers.DateField(
        input_formats=[DATE_FORMAT_SHORT, ],
        required=False,

    )
    type = serializers.ChoiceField(
        choices=INTERNAL_REPORT_TYPES,
        required=False
    )
    status = serializers.ChoiceField(
        choices=INTERNAL_REPORT_STATUSES,
        required=False
    )

    def get_start_date(self):
        start_date = self.validated_data.get('start_date', None)
        if start_date:
            return datetime.combine(start_date, datetime.min.time())
        else:
            return None

    def get_end_date(self):
        end_date = self.validated_data.get('end_date', None)
        if end_date:
            return datetime.combine(end_date, datetime.max.time())
        else:
            return None

    @staticmethod
    def validate_start_date(value):
        if value > date.today():
            raise ValidationError('Date should not be in future')
        return value

    @staticmethod
    def validate_end_date(value):
        if value > date.today():
            raise ValidationError('Date should not be in future')
        return value

    def validate(self, attrs):

        validated_data = super(
            InternalReportListRequestSerializer, self).validate(attrs)

        end_date = validated_data.get('end_date', None)
        start_date = validated_data.get('start_date', None)

        if end_date and start_date and end_date < start_date:
            raise ValidationError("'start_date' should not be greater than "
                                  "'end_date'")

        return validated_data


class InternalReportAssetsSerializer(serializers.ModelSerializer):
    """
    Serializer for assets internal report data
    """

    updated_at = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ('id', 'user_id', 'name', 'type', 'value',
                  'quantity', 'price', 'updated_at'
        )

    @staticmethod
    def get_updated_at(obj):
        if obj.financial_information:
            return format_date_short_or_none(
                obj.financial_information.market_data_updated)
        return None

    @staticmethod
    def get_price(obj):
        if obj.financial_information:
            return obj.financial_information.unit_price
        return None

    @staticmethod
    def get_user_id(obj):
        return obj.user.app_uid
