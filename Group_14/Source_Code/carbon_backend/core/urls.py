from django.urls import path, include

app_name = 'core'

urlpatterns = [
    # Include pollution awareness URLs
    path('pollution/', include('core.pollution_urls', namespace='pollution')),
    
    # Include enhanced NLP URLs
    path('nlp/', include('core.enhanced_nlp_urls', namespace='enhanced_nlp')),
    
    # Include predictive analytics URLs
    path('analytics/', include('core.predictive_analytics_urls', namespace='predictive_analytics')),
    
    # Include wallet URLs
    path('wallet/', include('core.wallet_urls', namespace='wallet')),
]