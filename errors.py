from rest_framework.status import HTTP_404_NOT_FOUND

from core.connect.api.error import Error
import logging

"""
New standard for errors.
<provider>-<HTTP_error_code>-<error>

Provider - Error
* Core Connect          : CCO
    - api_campany       : 0xx
    - common            : 1xx
    - core              : 2xx
    - datastorage       : 3xx
    - gdpr              : 4xx
    - historicals       : 5xx
    - importer          : 6xx
    - permission        : 7xx
    - pdf               : 8xx
    - internal_reports  : 9xx
* Analyse/Gearman       : GCA
* Core Interact         : CIN
* service_a             : AAA
* service_b             : BBB
* service_c             : CCC
* Core Analyse 2        : RCA
* service_d             : DDD
* service_e             : EEE

"""


class WrongFileFormat(Error):
    error = 'CCO-404-902'
    message = "File format is wrong. Could be csv or json"
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class DatesForReportAreRequired(Error):
    error = 'CCO-404-903'
    message = "Dates are required"
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR

    def __init__(self, field_name):
        super(DatesForReportAreRequired, self).__init__()
        self.description = "{field_name} is required".format(
            field_name=field_name)


class RequiredParameters(Error):
    error = 'CCO-404-904'
    message = "There are required parameters"
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR

    def __init__(self, param_name):
        super(RequiredParameters, self).__init__()
        self.description = "{param_name} is required".format(
            param_name=param_name)


class BrokenPortfolioComponent(Error):
    error = 'CCO-404-906'
    message = "The component does not have expected data"
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class NoInternalReportError(Error):
    error = 'CCO-404-907'
    message = 'Internal report not found'
    description = 'Internal report with requested ID does not exist'
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class CanNotDownloadReportError(Error):
    error = 'CCO-404-908'
    message = 'Can not download report'
    description = ('Report is being generated at the moment or '
                   'generation was failed')
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class ReportDataError(Error):
    error = 'CCO-404-909'
    message = 'Report data is not correct'
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class TransactionsOutOfQuarterError(Error):
    error = 'CCO-404-910'
    message = 'User portfolio is created after quarter end'
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR


class WrongInputValue(Error):
    error = 'CCO-404-911'
    message = 'Input value could be true, false or all'
    description = message
    status = HTTP_404_NOT_FOUND
    level = logging.ERROR
