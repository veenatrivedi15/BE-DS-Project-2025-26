from django.urls import path
from core.views.employer_views import dashboard

urlpatterns = [
    # Main dashboard
    path('dashboard/', dashboard, name='employer_dashboard'),
] 
from core.views.employer_views import dashboard

urlpatterns = [
    # Main dashboard
    path('dashboard/', dashboard, name='employer_dashboard'),
] 