from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    # Trip management endpoints
    path('', views.TripListView.as_view(), name='trip_list'),
    path('<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    path('start/', views.TripStartView.as_view(), name='trip_start'),
    path('<int:pk>/end/', views.TripEndView.as_view(), name='trip_end'),
    
    # Trip proof upload
    path('<int:pk>/upload-proof/', views.TripProofUploadView.as_view(), name='trip_proof_upload'),
    
    # Trip verification (admin only)
    path('<int:pk>/verify/', views.TripVerificationView.as_view(), name='trip_verify'),
    
    # Analytics and stats
    path('stats/', views.TripStatsView.as_view(), name='trip_stats'),
    
    # Carbon credit endpoints
    path('credits/', views.CreditListView.as_view(), name='credit_list'),
    path('credits/history/', views.CreditHistoryView.as_view(), name='credit_history'),
    path('credits/stats/', views.CreditStatsView.as_view(), name='credit_stats'),
    path('credits/employer-stats/', views.EmployerCreditStatsView.as_view(), name='employer_credit_stats'),
] 