from internal_reports import views

from django.conf.urls import url


urlpatterns = [
    url(r'^generate/active-users-list/$',
        views.GenerateActiveUsersView.as_view(dict(
            get='generate_active_users_list')),
        name='generate-active-users-list'),

    url(r'^generate/users-risk-score-list/$',
        views.GenerateUsersRiskScoreView.as_view(dict(
            get='generate_users_risk_score_list')),
        name='generate-risk-scores-list'),

    url(r'^generate/invalid-quarter-data/$',
        views.QuarterDataValidationView.as_view(dict(
            get='validate_quarter_data')),
        name='validate-quarter-data'),

    url(r'^generate/goals/$',
        views.GoalsReportView.as_view(dict(
            get='get_goals_report')),
        name='report-goals'),

    url(r'^generate/orders/$',
        views.GenerateOrdersView.as_view(dict(
            get='generate_orders')),
        name='generate-orders'),

    url(r'^generate/recurrent-orders/$',
        views.GenerateRecurrentOrdersView.as_view(dict(
            get='generate_recurrent_orders')),
        name='generate-recurrent-orders'),

    url(r'^generate/balances/$',
        views.GenerateBalancesView.as_view(dict(
            get='generate_balances')),
        name='generate-balances'),

    url(r'^generate/assets-list/$',
        views.GenerateAssetsView.as_view(dict(
            get='generate_assets_list')),
        name='generate-assets-list'),

    url(r'^list/$',
        views.GetReportsListView.as_view(dict(
            get='get_all')),
        name='list'),

    url(r'^types/$',
        views.GetReportsTypesView.as_view(dict(
            get='get_types')),
        name='types'),

    url(r'^statuses/$',
        views.GetReportStatusesView.as_view(dict(
            get='get_statuses')),
        name='statuses'),

    url(r'^view/$',
        views.GetReportView.as_view(dict(
            get='get_detailed_report')),
        name='view'),

    url(r'^download/$',
        views.DownloadReportView.as_view(dict(
            get='download_report')),
        name='download')
]
