from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Market offer endpoints
    path('offers/', views.MarketOfferListCreateView.as_view(), name='offer_list'),
    path('offers/<int:pk>/', views.MarketOfferDetailView.as_view(), name='offer_detail'),
    path('offers/<int:pk>/cancel/', views.MarketOfferCancelView.as_view(), name='offer_cancel'),
    
    # Transaction endpoints
    path('transactions/', views.TransactionListCreateView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<int:pk>/approve/', views.TransactionApprovalView.as_view(), name='transaction_approve'),
    path('transactions/<int:pk>/reject/', views.TransactionRejectView.as_view(), name='transaction_reject'),
    
    # Analytics and stats
    path('stats/', views.MarketStatsView.as_view(), name='market_stats'),
] 