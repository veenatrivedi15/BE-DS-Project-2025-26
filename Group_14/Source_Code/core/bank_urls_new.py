from django.urls import path
from core.views.bank_views import dashboard

urlpatterns = [
    # Main dashboard
    path('', dashboard, name='bank_dashboard'),
] 
from core.views.bank_views import dashboard

urlpatterns = [
    # Main dashboard
    path('', dashboard, name='bank_dashboard'),
] 