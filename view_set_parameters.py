START_DATE = dict(
    name="start_date",
    description="Start date of the period",
    required=True,
    type="string",
    location="query"
)

END_DATE = dict(
    name="end_date",
    description="End date of the period",
    required=True,
    type="string",
    location="query"
)

START_DATE_OPTIONAL = dict(
    name="start_date",
    description="Start date of the period",
    required=False,
    type="string",
    location="query"
)

END_DATE_OPTIONAL = dict(
    name="end_date",
    description="End date of the period",
    required=False,
    type="string",
    location="query"
)

CONSECUTIVE_DAYS = dict(
    name="consecutive_days",
    description="Number of expected consecutive days",
    required=True,
    type="integer",
    location="query"
)

AMOUNT_TO_VALIDATE = dict(
    name="amount_to_validate",
    description="Value to validate user's investment",
    required=True,
    type="integer",
    location="query"
)

FILE_FORMAT = dict(
    name="file_format",
    description="File format for report (csv or json; default is csv)",
    required=False,
    type="string",
    location="query"
)

UPPER_RISK_SCORE = dict(
    name="upper_risk_score",
    description="User with lower risk score will be in the list",
    required=False,
    type="integer",
    location="query"
)

LOWER_RISK_SCORE = dict(
    name="lower_risk_score",
    description="User with higher risk score will be in the list",
    required=False,
    type="integer",
    location="query"
)

DIRECT_DEBIT = dict(
    name="direct_debit",
    description="Recurrent orders with direct debit will be in the list "
                "(true/false/all)",
    required=False,
    type="string",
    location="query"
)

PERIOD_FINISHED = dict(
    name="period_finished",
    description="Finished recurrent orders will be in the list "
                "(true/false/all)",
    required=False,
    type="string",
    location="query"
)

GENERATE_ACTIVE_USERS_PARAMETERS_LIST = [
    START_DATE,
    END_DATE,
    CONSECUTIVE_DAYS,
    AMOUNT_TO_VALIDATE,
]

GENERATE_USERS_RISK_SCORE_PARAMETERS_LIST = [
    UPPER_RISK_SCORE,
    LOWER_RISK_SCORE,
]

GENERATE_VALIDATED_QUARTER_REPORT_DATA = [
    END_DATE_OPTIONAL
]

GENERATE_GOALS_PARAMETERS_LIST = [
    START_DATE_OPTIONAL,
    END_DATE_OPTIONAL
]

GENERATE_ORDERS_PARAMETERS_LIST = [
    START_DATE_OPTIONAL,
    END_DATE_OPTIONAL,
]

GENERATE_RECURRENT_ORDERS_PARAMETERS_LIST = [
    START_DATE_OPTIONAL,
    END_DATE_OPTIONAL,
    DIRECT_DEBIT,
    PERIOD_FINISHED
]