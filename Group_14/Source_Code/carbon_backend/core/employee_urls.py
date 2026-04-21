from django.urls import path, include
from core.views.employee_views import dashboard, trip_log, trips_list, manage_home_location, profile, update_profile, change_password, update_home_location, marketplace
from core.views.redemption_views import redeem_credits
from core.views.wallet_dashboard_views import wallet_dashboard, transaction_history, pending_transfers, transfer_details, wallet_verification, wallet_settings

urlpatterns = [
    path('dashboard/', dashboard, name='employee_dashboard'),
    path('trip/log/', trip_log, name='employee_trip_log'),
    path('trips/', trips_list, name='employee_trips'),
    path('home-location/', manage_home_location, name='employee_manage_home_location'),
    path('home-location/update/', update_home_location, name='employee_update_home_location'),
    
    # Profile
    path('profile/', profile, name='employee_profile'),
    path('profile/update/', update_profile, name='employee_update_profile'),
    path('profile/change-password/', change_password, name='employee_change_password'),
    
    # Marketplace
    path('marketplace/', marketplace, name='employee_marketplace'),
    
    # Credit Redemption
    path('redeem/', redeem_credits, name='employee_redeem_credits'),
    
    # Wallet
    path('wallet/', wallet_dashboard, name='wallet_dashboard'),
    path('wallet/transactions/', transaction_history, name='wallet_transactions'),
    path('wallet/transfers/pending/', pending_transfers, name='wallet_pending_transfers'),
    path('wallet/transfer/<uuid:transfer_id>/', transfer_details, name='wallet_transfer_details'),
    path('wallet/verification/', wallet_verification, name='wallet_verification'),
    path('wallet/settings/', wallet_settings, name='wallet_settings'),
    
    # Wallet API endpoints
    path('wallet/', include('core.wallet_urls', namespace='wallet')),
    
    # Pollution Awareness
    path('pollution/', include('core.pollution_urls', namespace='pollution')),
    
    # Enhanced NLP
    path('nlp/', include('core.enhanced_nlp_urls', namespace='enhanced_nlp')),
    
    # Predictive Analytics
    path('analytics/', include('core.predictive_analytics_urls', namespace='predictive_analytics')),
    
    # Gamification
    path('gamification/', include('core.gamification_urls', namespace='gamification')),
] 