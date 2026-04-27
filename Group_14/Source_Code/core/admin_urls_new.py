from django.urls import path
from core.views import admin_views

urlpatterns = [
    # Dashboard
    path('', admin_views.dashboard, name='admin_dashboard'),
    
    # User management
    path('users/', admin_views.users_list, name='admin_users'),
    path('users/create/', admin_views.create_user, name='admin_create_user'),
    path('users/<int:user_id>/', admin_views.user_detail, name='admin_user_detail'),
    path('users/<int:user_id>/approve/', admin_views.approve_user, name='admin_approve_user'),
    path('users/<int:user_id>/reject/', admin_views.reject_user, name='admin_reject_user'),
    path('users/hierarchy/', admin_views.user_hierarchy, name='admin_user_hierarchy'),
    
    # Employer management
    path('employers/', admin_views.employers_list, name='admin_employers'),
    path('employers/pending/', admin_views.employers_list, name='admin_pending_employers'),
    
    # Reports
    path('reports/', admin_views.reports, name='admin_reports'),
    path('reports/export/', admin_views.export_reports, name='admin_export_reports'),
    
    # Profile
    path('profile/', admin_views.admin_profile, name='admin_profile'),
    path('profile/update/', admin_views.admin_update_profile, name='admin_update_profile'),
    path('profile/change-password/', admin_views.admin_change_password, name='admin_change_password'),
    
    # Dashboard components that load dynamically
    path('recent-trips/', admin_views.dashboard_recent_trips, name='admin_dashboard_recent_trips'),
] 
from core.views import admin_views

urlpatterns = [
    # Dashboard
    path('', admin_views.dashboard, name='admin_dashboard'),
    
    # User management
    path('users/', admin_views.users_list, name='admin_users'),
    path('users/create/', admin_views.create_user, name='admin_create_user'),
    path('users/<int:user_id>/', admin_views.user_detail, name='admin_user_detail'),
    path('users/<int:user_id>/approve/', admin_views.approve_user, name='admin_approve_user'),
    path('users/<int:user_id>/reject/', admin_views.reject_user, name='admin_reject_user'),
    path('users/hierarchy/', admin_views.user_hierarchy, name='admin_user_hierarchy'),
    
    # Employer management
    path('employers/', admin_views.employers_list, name='admin_employers'),
    path('employers/pending/', admin_views.employers_list, name='admin_pending_employers'),
    
    # Reports
    path('reports/', admin_views.reports, name='admin_reports'),
    path('reports/export/', admin_views.export_reports, name='admin_export_reports'),
    
    # Profile
    path('profile/', admin_views.admin_profile, name='admin_profile'),
    path('profile/update/', admin_views.admin_update_profile, name='admin_update_profile'),
    path('profile/change-password/', admin_views.admin_change_password, name='admin_change_password'),
    
    # Dashboard components that load dynamically
    path('recent-trips/', admin_views.dashboard_recent_trips, name='admin_dashboard_recent_trips'),
] 