from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget

from internal_reports import models

from django.db.models import TextField

from tools.dates import format_date_long


@admin.register(models.InternalReport)
class InternalReportAdmin(admin.ModelAdmin):
    list_display = ('generated_date', 'type', 'status', 'context')
    list_filter = ('context', 'type', 'status')
    readonly_fields = ('context', 'type', 'status', 'generated_date', )
    exclude = ('generated', )

    formfield_overrides = {
        TextField: {'widget': JSONEditorWidget(mode='form')},
    }

    @staticmethod
    def generated_date(obj):
        return format_date_long(obj.generated)
