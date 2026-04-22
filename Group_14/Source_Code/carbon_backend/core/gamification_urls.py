"""
URL patterns for gamification features
"""
from django.urls import path
from .views.gamification_views import (
    gamification_dashboard, leaderboards_view, badges_view,
    progress_view, challenges_view, join_challenge,
    points_history, update_progress, get_leaderboard_data
)

app_name = 'gamification'

urlpatterns = [
    path('dashboard/', gamification_dashboard, name='dashboard'),
    path('leaderboards/', leaderboards_view, name='leaderboards'),
    path('badges/', badges_view, name='badges'),
    path('progress/', progress_view, name='progress'),
    path('challenges/', challenges_view, name='challenges'),
    path('points-history/', points_history, name='points_history'),
    
    # API endpoints
    path('api/join-challenge/<int:challenge_id>/', join_challenge, name='join_challenge'),
    path('api/update-progress/', update_progress, name='update_progress'),
    path('api/leaderboard-data/', get_leaderboard_data, name='leaderboard_data'),
]
