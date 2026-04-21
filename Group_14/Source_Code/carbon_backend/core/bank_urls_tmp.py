from django.urls import path
from .views.bank_views import bank_dashboard, bank_trading, BankReportsView, export_report

urlpatterns = [
    path('dashboard/', bank_dashboard, name='bank_dashboard'),
    path('trading/', bank_trading, name='bank_trading'),
    path('reports/', BankReportsView.as_view(), name='bank_reports'),
    path('reports/export/<str:report_type>/<str:date_range>/<str:format_type>/', 
         export_report, name='export_report'),
]
