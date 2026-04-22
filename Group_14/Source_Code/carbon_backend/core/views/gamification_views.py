"""
Views for gamification features - leaderboards, badges, progress
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal
import json

from core.gamification_service import (
    BadgeService, LeaderboardService, ProgressService,
    StreakService, ChallengeService, PointsService
)
from core.gamification_models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry,
    UserProgress, Streak, CommunityChallenge, ChallengeParticipant,
    UserPoints
)
from trips.models import Trip, CarbonCredit

# Set up logger
logger = logging.getLogger(__name__)

@login_required
def gamification_dashboard(request):
    """
    Main gamification dashboard showing badges, progress, and leaderboards
    """
    user = request.user
    
    try:
        # Get user's badges
        user_badges = BadgeService.get_user_badges(user, limit=6)
        badge_progress = BadgeService.get_badge_progress(user)
        
        # Get user's progress
        user_progress = ProgressService.get_user_progress(user)
        
        # Get user's streaks
        user_streaks = StreakService.get_user_streaks(user)
        
        # Get user's points
        total_points = PointsService.get_user_total_points(user)
        recent_points = PointsService.get_user_points_history(user, limit=5)
        
        # Get leaderboard rankings
        weekly_carbon_rank = LeaderboardService.get_user_rank(user, 'weekly', 'carbon_saved')
        weekly_trips_rank = LeaderboardService.get_user_rank(user, 'weekly', 'trips_count')
        
        # Get active challenges
        active_challenges = ChallengeService.get_active_challenges()
        user_challenges = ChallengeParticipant.objects.filter(
            user=user,
            challenge__status='active'
        ).select_related('challenge')
        
        # Convert QuerySets to lists for JSON serialization
        user_badges_list = list(user_badges) if user_badges else []
        badge_progress_list = list(user_progress) if user_progress else []
        user_streaks_list = list(user_streaks) if user_streaks else []
        recent_points_list = list(recent_points) if recent_points else []
        active_challenges_list = []
        for participant in user_challenges:
            active_challenges_list.append({
                'id': participant.challenge.id,
                'title': participant.challenge.title if participant.challenge else 'Unknown Challenge',
                'description': participant.challenge.description if participant.challenge else '',
                'status': participant.challenge.status if participant.challenge else 'active',
                'progress': participant.current_value or 0,
                'target': participant.challenge.target_value if participant.challenge else 0,
                'progress_percentage': (participant.current_value / participant.challenge.target_value * 100) if participant.challenge and participant.challenge.target_value > 0 else 0,
                'action_text': 'Join Challenge'  # CommunityChallenge doesn't have action_text field
            })
        
        context = {
            'user_badges': user_badges_list,
            'badge_progress': badge_progress_list,
            'user_progress': user_progress,
            'user_streaks': user_streaks_list,
            'total_points': total_points or 0,
            'recent_points': recent_points_list,
            'weekly_carbon_rank': weekly_carbon_rank,
            'weekly_trips_rank': weekly_trips_rank,
            'active_challenges': active_challenges_list,
            'user_challenges': active_challenges_list,
            'page_title': 'Achievements Dashboard'
        }
        
    except Exception as e:
        logger.error(f"Error in gamification_dashboard: {str(e)}")
        # Fallback context with safe defaults
        context = {
            'user_badges': [],
            'badge_progress': [],
            'user_progress': [],
            'user_streaks': [],
            'total_points': 0,
            'recent_points': [],
            'weekly_carbon_rank': None,
            'weekly_trips_rank': None,
            'active_challenges': [],
            'user_challenges': [],
            'page_title': 'Achievements Dashboard'
        }
    
    return render(request, 'gamification/dashboard.html', context)


@login_required
def leaderboards_view(request):
    """
    View all leaderboards
    """
    leaderboard_type = request.GET.get('type', 'weekly')
    category = request.GET.get('category', 'carbon_saved')
    
    # Get leaderboard data
    leaderboard_data = LeaderboardService.get_leaderboard_data(
        leaderboard_type, category, limit=50
    )
    
    if not leaderboard_data:
        messages.warning(request, 'Leaderboard not available or not updated yet.')
        return redirect('gamification:dashboard')
    
    # Get user's rank in this leaderboard
    user_rank = LeaderboardService.get_user_rank(request.user, leaderboard_type, category)
    
    # Get user's rankings for overview
    weekly_carbon_rank = LeaderboardService.get_user_rank(request.user, 'weekly', 'carbon_saved')
    weekly_trip_rank = LeaderboardService.get_user_rank(request.user, 'weekly', 'trips_count')
    monthly_carbon_rank = LeaderboardService.get_user_rank(request.user, 'monthly', 'carbon_saved')
    all_time_rank = LeaderboardService.get_user_rank(request.user, 'all_time', 'carbon_saved')
    
    # Get available leaderboard types and categories
    leaderboard_types = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('all_time', 'All Time')
    ]
    
    categories = [
        ('carbon_saved', 'Carbon Saved'),
        ('trips_count', 'Number of Trips'),
        ('badges_count', 'Badges Earned'),
        ('points', 'Total Points')
    ]
    
    context = {
        'leaderboard_data': leaderboard_data,
        'user_rank': user_rank,
        'current_type': leaderboard_type,
        'current_category': category,
        'leaderboard_types': leaderboard_types,
        'categories': categories,
        'weekly_carbon_rank': weekly_carbon_rank,
        'weekly_trip_rank': weekly_trip_rank,
        'monthly_carbon_rank': monthly_carbon_rank,
        'all_time_rank': all_time_rank,
        'page_title': 'Leaderboards'
    }
    
    return render(request, 'gamification/leaderboards.html', context)


@login_required
def badges_view(request):
    """
    View user's badges and progress
    """
    user = request.user
    
    # Get earned badges
    earned_badges = BadgeService.get_user_badges(user)
    
    # Get badge progress
    badge_progress = BadgeService.get_badge_progress(user)
    earned_badge_ids = [user_badge.badge_id for user_badge in earned_badges]
    progress_badge_ids = [progress['badge'].id for progress in badge_progress]
    
    # Group badges by category
    badges_by_category = {}
    for badge in Badge.objects.filter(is_active=True):
        category = badge.get_category_display()
        if category not in badges_by_category:
            badges_by_category[category] = []
        badges_by_category[category].append(badge)
    
    # Check for newly earned badges
    newly_awarded = BadgeService.check_and_award_badges(user)
    if newly_awarded:
        messages.success(request, f'Congratulations! You earned {len(newly_awarded)} new badge(s)!')
    
    context = {
        'earned_badges': earned_badges,
        'badge_progress': badge_progress,
        'earned_badge_ids': earned_badge_ids,
        'progress_badge_ids': progress_badge_ids,
        'badges_by_category': badges_by_category,
        'page_title': 'My Badges'
    }
    
    return render(request, 'gamification/badges.html', context)


@login_required
def progress_view(request):
    """
    View user's progress towards goals
    """
    user = request.user
    
    # Get user's progress
    user_progress = ProgressService.get_user_progress(user)
    
    # Update progress
    ProgressService.update_user_progress(user)
    
    # Get progress statistics
    completed_goals = user_progress.filter(is_completed=True).count()
    active_goals = user_progress.filter(is_completed=False).count()
    
    # Calculate overall progress percentage
    if user_progress.exists():
        overall_progress = sum(float(p.percentage_complete) for p in user_progress) / user_progress.count()
    else:
        overall_progress = 0
    
    context = {
        'user_progress': user_progress,
        'completed_goals': completed_goals,
        'active_goals': active_goals,
        'overall_progress': round(overall_progress, 1),
        'page_title': 'My Progress'
    }
    
    return render(request, 'gamification/progress.html', context)


@login_required
def challenges_view(request):
    """
    View community challenges
    """
    user = request.user
    
    # Get active challenges
    active_challenges = ChallengeService.get_active_challenges()
    
    # Get user's challenge participations
    user_participations = ChallengeParticipant.objects.filter(
        user=user
    ).select_related('challenge').order_by('-joined_at')
    joined_challenge_ids = list(user_participations.values_list('challenge_id', flat=True))
    
    # Update challenge progress
    ChallengeService.update_challenge_progress(user)
    
    # Get challenge statistics
    completed_challenges = user_participations.filter(is_completed=True).count()
    active_user_challenges = user_participations.filter(
        is_completed=False,
        challenge__status='active'
    ).count()
    
    context = {
        'active_challenges': active_challenges,
        'user_participations': user_participations,
        'joined_challenge_ids': joined_challenge_ids,
        'completed_challenges': completed_challenges,
        'active_user_challenges': active_user_challenges,
        'page_title': 'Community Challenges'
    }
    
    return render(request, 'gamification/challenges.html', context)


@login_required
def join_challenge(request, challenge_id):
    """
    Join a community challenge
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    participant = ChallengeService.join_challenge(request.user, challenge_id)
    
    if participant:
        messages.success(request, f'Successfully joined the challenge!')
        return JsonResponse({
            'success': True,
            'message': 'Successfully joined the challenge!'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Challenge not found or not active.'
        })


@login_required
def points_history(request):
    """
    View user's points history
    """
    user = request.user
    
    # Get points history
    points_history = PointsService.get_user_points_history(user, limit=50)
    
    # Get points statistics
    total_points = PointsService.get_user_total_points(user)
    
    # Calculate points by type
    points_by_type = UserPoints.objects.filter(user=user).values('points_type').annotate(
        total=Sum('points'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'points_history': points_history,
        'total_points': total_points,
        'points_by_type': points_by_type,
        'page_title': 'Points History'
    }
    
    return render(request, 'gamification/points_history.html', context)


@login_required
def update_progress(request):
    """
    API endpoint to update user progress
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        # Update all progress types
        ProgressService.update_user_progress(request.user)
        StreakService.update_user_streaks(request.user)
        ChallengeService.update_challenge_progress(request.user)
        
        # Check for new badges
        newly_awarded = BadgeService.check_and_award_badges(request.user)
        
        return JsonResponse({
            'success': True,
            'new_badges': len(newly_awarded),
            'message': 'Progress updated successfully!'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def get_leaderboard_data(request):
    """
    API endpoint to get leaderboard data
    """
    leaderboard_type = request.GET.get('type', 'weekly')
    category = request.GET.get('category', 'carbon_saved')
    limit = int(request.GET.get('limit', 20))
    
    leaderboard_data = LeaderboardService.get_leaderboard_data(
        leaderboard_type, category, limit=limit
    )
    
    if not leaderboard_data:
        return JsonResponse({
            'success': False,
            'message': 'Leaderboard data not available'
        })
    
    # Format data for JSON response
    entries_data = []
    for entry in leaderboard_data['entries']:
        entries_data.append({
            'rank': entry.rank,
            'user_name': entry.user.get_full_name() or entry.user.email,
            'value': float(entry.value),
            'previous_rank': entry.previous_rank
        })
    
    return JsonResponse({
        'success': True,
        'leaderboard': {
            'name': leaderboard_data['leaderboard'].name,
            'type': leaderboard_data['leaderboard'].get_leaderboard_type_display(),
            'category': leaderboard_data['leaderboard'].get_category_display(),
            'total_participants': leaderboard_data['total_participants']
        },
        'entries': entries_data,
        'user_rank': LeaderboardService.get_user_rank(request.user, leaderboard_type, category)
    })
