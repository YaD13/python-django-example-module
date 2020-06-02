FILE_FORMAT_CSV = 'csv'
FILE_FORMAT_JSON = 'json'

MIME_TYPE_CSV = 'text/csv'

INTERNAL_REPORT_ACTIVE_USERS = 0
INTERNAL_REPORT_USER_RISK_SCORES = 1
INTERNAL_REPORT_QUARTER_VALIDATION = 2
INTERNAL_REPORT_GOALS = 3
INTERNAL_REPORT_RECURRENT_ORDERS = 4
INTERNAL_REPORT_ORDERS = 5
INTERNAL_REPORT_BALANCES = 6
INTERNAL_REPORT_ASSETS = 7

INTERNAL_REPORT_TYPES = (
    (INTERNAL_REPORT_ACTIVE_USERS, 'Active users'),
    (INTERNAL_REPORT_USER_RISK_SCORES, 'User risk scores'),
    (INTERNAL_REPORT_QUARTER_VALIDATION, 'Quarter validation'),
    (INTERNAL_REPORT_GOALS, 'Goals'),
    (INTERNAL_REPORT_RECURRENT_ORDERS, 'Recurrent orders'),
    (INTERNAL_REPORT_ORDERS, 'Orders'),
    (INTERNAL_REPORT_BALANCES, 'Balances'),
    (INTERNAL_REPORT_ASSETS, 'Assets'),
)

INTERNAL_REPORT_CSV_COLUMNS = {
    INTERNAL_REPORT_ACTIVE_USERS: [
        'personid',
        'consecutive_days',
        'average_value_of_consecutive_days',
        'first_date_reported',
        'position_average_value',
        'position_first_date_reported',
        'position_start_date',
        'position_start_value',
        'position_end_date',
        'position_end_value',
        'error'
    ],
    INTERNAL_REPORT_ASSETS: [
        'id',
        'user_id',
        'name',
        'type',
        'value',
        'quantity',
        'price',
        'updated_at'
    ],
    INTERNAL_REPORT_USER_RISK_SCORES: [
        'user_id',
        'selected_user_risk_score',
        'suggested_user_risk_score',
        'risk_score_date_save',
        'investments_portfolio_value'
    ],
    INTERNAL_REPORT_QUARTER_VALIDATION: [
        'user_id',
        'start_date',
        'end_date',
        'context',
        'revenue_is_valid',
        'start_values_are_valid',
        'end_values_are_valid',
        'transaction_and_revenue_valid',
        'is_cash_component_valid',
        'revenue_per_asset_valid',
        'ptf_before_last_sell',
        'flow_before_last_sell',
        'last_sell_date',
        'net_inflow_outflow',
        'portfolio_start_value',
        'portfolio_end_value',
        'asset_container_id',
        'interest_paid',
        'accrued_interest',
        'return_in_cash',
        'cumulative_performance',
        'error'
    ],
    INTERNAL_REPORT_GOALS: [
        'user_id',
        'goal_id',
        'name',
        'type',
        'value',
        'created',
        'start_date',
        'end_date',
        'frequency'
    ],
    INTERNAL_REPORT_RECURRENT_ORDERS: [
        'user_id',
        'status',
        'amount',
        'frequency_type',
        'frequency',
        'order_start_date',
        'order_next_date',
        'order_end_date',
        'action',
        'orders_created',
        'number_of_retries',
        'direct_debit',
        'created',
        'mandate_id',
        'direct_debit_date',
        'cancel_after_next_execution',
    ],
    INTERNAL_REPORT_ORDERS: [
        'user_id',
        'type',
        'date',
        'value',
        'status',
        'rebalancing',
    ],
    INTERNAL_REPORT_BALANCES: [
        'user_id',
        'name',
        'type',
        'total_value',
    ]
}

INTERNAL_REPORT_STATUS_GENERATING = 0
INTERNAL_REPORT_STATUS_READY = 1
INTERNAL_REPORT_STATUS_FAILED = 2

INTERNAL_REPORT_STATUSES = (
    (INTERNAL_REPORT_STATUS_GENERATING, 'Generating'),
    (INTERNAL_REPORT_STATUS_READY, 'Ready'),
    (INTERNAL_REPORT_STATUS_FAILED, 'Failed')
)
