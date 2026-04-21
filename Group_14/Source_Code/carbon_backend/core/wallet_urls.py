"""
Digital Carbon Credit & Wallet System URL Configuration
"""

from django.urls import path
from core.views import wallet_views

app_name = 'wallet'

urlpatterns = [
    # Wallet balance and stats
    path('balance/', wallet_views.wallet_balance, name='balance'),
    path('stats/', wallet_views.wallet_stats, name='stats'),
    path('summary/', wallet_views.wallet_summary, name='summary'),
    
    # Transactions
    path('transactions/', wallet_views.transaction_history, name='transactions'),
    path('add-credits/', wallet_views.add_credits, name='add_credits'),
    
    # Transfers
    path('transfer/', wallet_views.transfer_credits, name='transfer'),
    path('transfer/<uuid:transfer_id>/', wallet_views.transfer_status, name='transfer_status'),
    path('transfers/pending/', wallet_views.pending_transfers, name='pending_transfers'),
    path('transfer/validate/', wallet_views.validate_transfer, name='validate_transfer'),
    
    # Verification and security
    path('verify/', wallet_views.verify_wallet, name='verify'),
    
    # System endpoints
    path('process-trip-rewards/', wallet_views.process_trip_rewards, name='process_trip_rewards'),
]
