from django.urls import path
from .views.admin_views import SystemConfigListView, SystemConfigDetailView
from .views.admin_views import AdminStatsView, AdminDashboardView
from .views.admin_views import PendingEmployersView, PendingTransactionsView
from .views.admin_views import BankAdminCreateView
from .views.bank_views import bank_dashboard, bank_trading, BankReportsView, export_report

app_name = 'core'

urlpatterns = [
    # System config endpoints (admin only)
    path('config/', SystemConfigListView.as_view(), name='config_list'),
    path('config/<int:pk>/', SystemConfigDetailView.as_view(), name='config_detail'),
    
    # Admin-specific endpoints
    path('admin/stats/', AdminStatsView.as_view(), name='admin_stats'),
    path('admin/dashboard/stats/', AdminDashboardView.as_view(), name='admin_dashboard_stats'),
    path('admin/employers/pending/', PendingEmployersView.as_view(), name='pending_employers'),
    path('admin/transactions/pending/', PendingTransactionsView.as_view(), name='pending_transactions'),
    path('admin/bank-admins/', BankAdminCreateView.as_view(), name='create_bank_admin'),

    # Bank URLs
    path('bank/dashboard/', bank_dashboard, name='bank_dashboard'),
    path('bank/trading/', bank_trading, name='bank_trading'),
    path('bank/reports/', BankReportsView.as_view(), name='bank_reports'),
    path('bank/export-report/<str:report_type>/<str:date_range>/<str:format_type>/', 
         export_report, name='export_report'),
]
