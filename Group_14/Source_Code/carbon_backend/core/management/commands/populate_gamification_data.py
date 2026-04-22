"""
Management command to populate initial gamification data
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from core.gamification_models import Badge, Leaderboard, CommunityChallenge
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate initial gamification data (badges, leaderboards, challenges)'

    def handle(self, *args, **options):
        self.stdout.write('Creating gamification data...')
        
        # Create badges
        self.stdout.write('Creating badges...')
        badges = [
            # Trip badges
            {
                'name': 'First Step',
                'description': 'Complete your first sustainable trip',
                'badge_type': 'bronze',
                'category': 'trips',
                'icon': '🚶',
                'condition_type': 'trips_count',
                'condition_value': 1,
                'points': 10
            },
            {
                'name': 'Commuter',
                'description': 'Complete 10 sustainable trips',
                'badge_type': 'bronze',
                'category': 'trips',
                'icon': '🚴',
                'condition_type': 'trips_count',
                'condition_value': 10,
                'points': 25
            },
            {
                'name': 'Eco Warrior',
                'description': 'Complete 50 sustainable trips',
                'badge_type': 'silver',
                'category': 'trips',
                'icon': '🌿',
                'condition_type': 'trips_count',
                'condition_value': 50,
                'points': 100
            },
            {
                'name': 'Carbon Master',
                'description': 'Complete 100 sustainable trips',
                'badge_type': 'gold',
                'category': 'trips',
                'icon': '🏆',
                'condition_type': 'trips_count',
                'condition_value': 100,
                'points': 250
            },
            
            # Carbon saving badges
            {
                'name': 'Carbon Saver',
                'description': 'Save 5 kg of CO2',
                'badge_type': 'bronze',
                'category': 'carbon',
                'icon': '🌍',
                'condition_type': 'carbon_saved',
                'condition_value': 5,
                'points': 15
            },
            {
                'name': 'Climate Hero',
                'description': 'Save 25 kg of CO2',
                'badge_type': 'silver',
                'category': 'carbon',
                'icon': '🦸',
                'condition_type': 'carbon_saved',
                'condition_value': 25,
                'points': 75
            },
            {
                'name': 'Planet Protector',
                'description': 'Save 100 kg of CO2',
                'badge_type': 'gold',
                'category': 'carbon',
                'icon': '🛡️',
                'condition_type': 'carbon_saved',
                'condition_value': 100,
                'points': 200
            },
            
            # Streak badges
            {
                'name': 'Streak Starter',
                'description': 'Maintain a 3-day streak',
                'badge_type': 'bronze',
                'category': 'streak',
                'icon': '🔥',
                'condition_type': 'streak_days',
                'condition_value': 3,
                'points': 20
            },
            {
                'name': 'Week Warrior',
                'description': 'Maintain a 7-day streak',
                'badge_type': 'silver',
                'category': 'streak',
                'icon': '⚔️',
                'condition_type': 'streak_days',
                'condition_value': 7,
                'points': 50
            },
            {
                'name': '30 Day Master',
                'description': 'Maintain a 30-day streak',
                'badge_type': 'gold',
                'category': 'streak',
                'icon': '👑',
                'condition_type': 'streak_days',
                'condition_value': 30,
                'points': 150
            },
            
            # Special badges
            {
                'name': 'Early Adopter',
                'description': 'Joined in the first month',
                'badge_type': 'special',
                'category': 'special',
                'icon': '🌟',
                'condition_type': 'special_condition',
                'condition_value': 1,
                'points': 100
            },
            {
                'name': 'Community Leader',
                'description': 'Top 10 in monthly leaderboard',
                'badge_type': 'platinum',
                'category': 'community',
                'icon': '👥',
                'condition_type': 'special_condition',
                'condition_value': 1,
                'points': 300
            }
        ]
        
        created_badges = 0
        for badge_data in badges:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if created:
                created_badges += 1
                self.stdout.write(f'Created badge: {badge.name}')
            else:
                self.stdout.write(f'Badge already exists: {badge.name}')
        
        self.stdout.write(f'Created {created_badges} new badges')
        
        # Create leaderboards
        self.stdout.write('\nCreating leaderboards...')
        leaderboards = [
            # Daily leaderboards
            {'name': 'Daily Carbon Saver', 'leaderboard_type': 'daily', 'category': 'carbon_saved'},
            {'name': 'Daily Trip Master', 'leaderboard_type': 'daily', 'category': 'trips_count'},
            
            # Weekly leaderboards
            {'name': 'Weekly Carbon Champion', 'leaderboard_type': 'weekly', 'category': 'carbon_saved'},
            {'name': 'Weekly Trip Champion', 'leaderboard_type': 'weekly', 'category': 'trips_count'},
            {'name': 'Weekly Badge Hunter', 'leaderboard_type': 'weekly', 'category': 'badges_count'},
            
            # Monthly leaderboards
            {'name': 'Monthly Carbon Hero', 'leaderboard_type': 'monthly', 'category': 'carbon_saved'},
            {'name': 'Monthly Trip Master', 'leaderboard_type': 'monthly', 'category': 'trips_count'},
            {'name': 'Monthly Points Leader', 'leaderboard_type': 'monthly', 'category': 'points'},
            
            # All-time leaderboards
            {'name': 'All Time Carbon Legend', 'leaderboard_type': 'all_time', 'category': 'carbon_saved'},
            {'name': 'All Time Trip Legend', 'leaderboard_type': 'all_time', 'category': 'trips_count'},
            {'name': 'All Time Points Master', 'leaderboard_type': 'all_time', 'category': 'points'},
        ]
        
        created_leaderboards = 0
        for lb_data in leaderboards:
            leaderboard, created = Leaderboard.objects.get_or_create(
                leaderboard_type=lb_data['leaderboard_type'],
                category=lb_data['category'],
                defaults=lb_data
            )
            if created:
                created_leaderboards += 1
                self.stdout.write(f'Created leaderboard: {leaderboard.name}')
            else:
                self.stdout.write(f'Leaderboard already exists: {leaderboard.name}')
        
        self.stdout.write(f'Created {created_leaderboards} new leaderboards')
        
        # Create sample challenges
        self.stdout.write('\nCreating community challenges...')
        from django.utils import timezone
        import datetime
        
        challenges = [
            {
                'title': 'November Green Challenge',
                'description': 'Save 50 kg of CO2 this November! Every sustainable trip counts towards our collective goal.',
                'challenge_type': 'individual',
                'target_metric': 'carbon_saved',
                'target_value': 50,
                'reward_points': 200,
                'start_date': timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                'end_date': timezone.now().replace(day=30, hour=23, minute=59, second=59, microsecond=999999),
                'status': 'active'
            },
            {
                'title': 'December Commute Challenge',
                'description': 'Complete 30 sustainable trips in December. Let\'s make our commute green!',
                'challenge_type': 'individual',
                'target_metric': 'trips_count',
                'target_value': 30,
                'reward_points': 150,
                'start_date': timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                'end_date': timezone.now().replace(day=31, hour=23, minute=59, second=59, microsecond=999999),
                'status': 'upcoming'
            },
            {
                'title': 'Company Green Cup',
                'description': 'Company-wide competition to save the most CO2 this quarter. Top performers get special recognition!',
                'challenge_type': 'company',
                'target_metric': 'carbon_saved',
                'target_value': 500,
                'reward_points': 500,
                'start_date': timezone.now() - datetime.timedelta(days=15),
                'end_date': timezone.now() + datetime.timedelta(days=75),
                'status': 'active'
            }
        ]
        
        created_challenges = 0
        for challenge_data in challenges:
            challenge, created = CommunityChallenge.objects.get_or_create(
                title=challenge_data['title'],
                defaults=challenge_data
            )
            if created:
                created_challenges += 1
                self.stdout.write(f'Created challenge: {challenge.title}')
            else:
                self.stdout.write(f'Challenge already exists: {challenge.title}')
        
        self.stdout.write(f'Created {created_challenges} new challenges')
        
        # Assign reward badges to challenges
        carbon_master_badge = Badge.objects.filter(name='Carbon Master').first()
        if carbon_master_badge:
            CommunityChallenge.objects.filter(title='November Green Challenge').update(reward_badge=carbon_master_badge)
        
        planet_protector_badge = Badge.objects.filter(name='Planet Protector').first()
        if planet_protector_badge:
            CommunityChallenge.objects.filter(title='Company Green Cup').update(reward_badge=planet_protector_badge)
        
        self.stdout.write(self.style.SUCCESS('Gamification data population completed successfully!'))
        self.stdout.write('\nSummary:')
        self.stdout.write(f'- Badges: {Badge.objects.count()} total')
        self.stdout.write(f'- Leaderboards: {Leaderboard.objects.count()} total')
        self.stdout.write(f'- Challenges: {CommunityChallenge.objects.count()} total')
