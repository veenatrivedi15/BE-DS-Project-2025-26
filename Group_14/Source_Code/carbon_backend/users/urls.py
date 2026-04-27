from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User profile endpoints
    path('me/', views.CurrentUserView.as_view(), name='current_user'),
    
    # Registration endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('employers/register/', views.EmployerRegistrationView.as_view(), name='employer_register'),
    path('employees/register/', views.EmployeeRegistrationView.as_view(), name='employee_register'),
    path('registration/pending-approval/', views.PendingApprovalView.as_view(), name='pending_approval'),
    
    # Employer management endpoints
    path('employers/', views.EmployerListView.as_view(), name='employer_list'),
    path('employers/<int:pk>/', views.EmployerDetailView.as_view(), name='employer_detail'),
    path('employers/<int:pk>/approve/', views.EmployerApprovalView.as_view(), name='employer_approve'),
    
    # Employee management endpoints
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/approve/', views.EmployeeApprovalView.as_view(), name='employee_approve'),
    
    # Location management endpoints
    path('locations/', views.LocationListCreateView.as_view(), name='location_list'),
    path('locations/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
] 