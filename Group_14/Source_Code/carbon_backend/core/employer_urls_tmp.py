from django.urls import path
from .views.employer_views import employer_dashboard, employer_employees
from .views.employer_views import employer_marketplace, employer_reports

urlpatterns = [
    path('dashboard/', employer_dashboard, name='employer_dashboard'),
    path('employees/', employer_employees, name='employer_employees'),
    path('marketplace/', employer_marketplace, name='employer_marketplace'),
    path('reports/', employer_reports, name='employer_reports'),
]
