from django.urls import path
from core.views.employee_views import dashboard

urlpatterns = [
    # Main dashboard
    path('dashboard/', dashboard, name='employee_dashboard'),
] 
from core.views.employee_views import dashboard

urlpatterns = [
    # Main dashboard
    path('dashboard/', dashboard, name='employee_dashboard'),
] 