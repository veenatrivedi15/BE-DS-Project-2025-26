from django.urls import path
from .views.employee_views import employee_dashboard, employee_trip_log
from .views.employee_views import employee_trips, employee_marketplace, employee_profile

urlpatterns = [
    path('dashboard/', employee_dashboard, name='employee_dashboard'),
    path('trip-log/', employee_trip_log, name='employee_trip_log'),
    path('trips/', employee_trips, name='employee_trips'),
    path('marketplace/', employee_marketplace, name='employee_marketplace'),
    path('profile/', employee_profile, name='employee_profile'),
]
