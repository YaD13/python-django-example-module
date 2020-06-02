import datetime

import pandas as pd

import json

from internal_reports.constants import *
from internal_reports.errors import (
    DatesForReportAreRequired,
    RequiredParameters,
    WrongFileFormat,
    ReportDataError,
    WrongInputValue
)
from tools.dates import (
    read_date_short,
    format_date_long,
    format_date_short
)
from rest_framework.views import (
    status,
    Response
)


def get_date(data_srt, field_name):
    """
    Get date from string or raise an exception
    :param data_srt: date string
    :param field_name: field name
    :return: datetime object
    """
    if data_srt:
        return read_date_short(data_srt).date()
    else:
        raise DatesForReportAreRequired(field_name=field_name)


def get_required_int_value(value_str, param_name):
    """
    Get int value from string or raise an exception
    :param value_str: string value
    :param param_name: parameter name
    :return: integer
    """
    if value_str:
        return int(value_str)
    else:
        raise RequiredParameters(param_name=param_name)


def get_int_value(value_str):
    if value_str:
        return int(value_str)
    else:
        return None


def prepare_response(report, file_format):
    """
    Prepare response
    :param report: Internal report instance
    :param file_format: file format fot the report
    :return: response object
    """

    data = report.get_data()

    if isinstance(data, str):
        raise ReportDataError(
            description=data
        )

    filename = '{type}_on_{date}.{format}'.format(
        type=report.get_type_display(),
        date=format_date_long(report.generated),
        format=file_format).replace(' ', '_')
    sort_by_user_id = (data[0].get('user_id')
                       if isinstance(data, list) else False)

    if file_format == FILE_FORMAT_JSON:
        response = prepare_json_response(data, sort_by_user_id, filename)
    else:
        response = prepare_csv_response(data, sort_by_user_id, filename, report)

    return response


def prepare_json_response(data, sort_by_user_id, filename):
    """
    Prepare response in JSON format
    :param data: report data
    :param sort_by_user_id: should data be sorted by users or not
    :param filename: filename
    :return: response with formatted data and filename
    """

    if sort_by_user_id:
        data = sorted(data, key=lambda k: k['user_id'])

    return Response(data={'report': json.dumps(data, indent=2),
                          'filename': filename},
                    status=status.HTTP_200_OK)


def prepare_csv_response(data, sort_by_user_id, filename, report):
    """
    Prepare response in csv format
    :param data: report data
    :param sort_by_user_id: should data be sorted by users or not
    :param filename: filename
    :param report: InternalReport instance
    :return: response with formatted data and filename
    """

    users_list_df = (pd.DataFrame(data=data).sort_values('user_id')
                     if sort_by_user_id else pd.DataFrame(data=data))

    data = users_list_df.to_csv(
        index=False,
        columns=report.get_csv_columns())

    return Response(data={'report': data,
                          'filename': filename},
                    status=status.HTTP_200_OK)


def get_end_date_from_request(parameters):
    """
    Read end date from request parameters
    :param parameters: Request parameters dict
    :return: quarter report end
    """

    end_date_str = parameters.get('end_date', None)
    return (read_date_short(end_date_str).date()
            if end_date_str
            else datetime.datetime.now().date())


def get_date_from_request(parameters, name):
    """
    Read date from request parameters
    :param parameters: Request parameters dict
    :return: quarter report end
    """

    date_str = parameters.get(name, None)
    return (read_date_short(date_str).date()
            if date_str else None)


def format_date_short_or_none(date):
    """
    Format date to format YYYY-MM-DD if it's present
    :param date: date object
    :return: formatted string or None
    """

    if date:
        return format_date_short(date)
    return None


def get_file_format_from_request(parameters):
    """
    Read and validate file format from request parameters
    :param parameters: Request parameters dict
    :return: file format value
    """

    file_format = parameters.get('file_format', FILE_FORMAT_CSV).lower()

    if file_format not in [FILE_FORMAT_CSV, FILE_FORMAT_JSON]:
        raise WrongFileFormat

    return file_format


def check_for_true_false_all(parameters, key):
    """
    Check dict for key and check item for expected value
    :param parameters: dict
    :param key: key
    :return: 'True', 'False' or None
    """
    param = parameters.get(key)
    if param and param.lower() in ['true', 'false']:
        return param.capitalize()
    elif param == 'all' or param is None:
        return None
    else:
        raise WrongInputValue


def filter_queryset_by_date_range(queryset, start_date, end_date, field_name):
    """
    Filter queryset by start and end date
    :param queryset: queryset
    :param start_date: date obj
    :param end_date: date obj
    :param field_name: name of the field in db for filter by
    :return: queryset
    """

    if end_date:

        max_time = datetime.datetime.max.time()

        end_date = datetime.datetime.combine(end_date, max_time)

        filter_end_date = {'{}__lte'.format(field_name): end_date}

        queryset = queryset.filter(
            **filter_end_date
        )

    if start_date:
        filter_start_date = {'{}__gte'.format(field_name): start_date}

        queryset = queryset.filter(
            **filter_start_date
        )

    return queryset
