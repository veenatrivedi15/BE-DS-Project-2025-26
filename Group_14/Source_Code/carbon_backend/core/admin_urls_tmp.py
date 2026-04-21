from django.urls import path
from .views.admin_views import AdminStatsView, AdminDashboardView
from .views.admin_views import PendingEmployersView, PendingTransactionsView
from .views.admin_views import BankAdminCreateView

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('stats/', AdminStatsView.as_view(), name='admin_stats'),
    path('employers/pending/', PendingEmployersView.as_view(), name='pending_employers'),
    path('transactions/pending/', PendingTransactionsView.as_view(), name='pending_transactions'),
    path('bank-admins/', BankAdminCreateView.as_view(), name='create_bank_admin'),
]
