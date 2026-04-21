"""
Views for handling user notifications.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from core.models import Notification
from marketplace.models import EmployeeCreditOffer, TransactionNotification
import json

@login_required
def get_notifications(request):
    """
    Get all notifications for the current user (AJAX endpoint).
    """
    # Get both core notifications and marketplace notifications
    core_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    marketplace_notifications = TransactionNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    # Combine and format notifications
    notifications = []
    
    for notif in core_notifications:
        notifications.append({
            'id': notif.id,
            'type': 'core',
            'notification_type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat(),
            'link': notif.link or '',
        })
    
    for notif in marketplace_notifications:
        notifications.append({
            'id': notif.id,
            'type': 'marketplace',
            'notification_type': notif.notification_type,
            'title': 'Transaction Update',
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat(),
            'link': '',
        })
    
    # Sort by created_at
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    unread_count = sum(1 for n in notifications if not n['is_read'])
    
    return JsonResponse({
        'notifications': notifications[:20],
        'unread_count': unread_count
    })

@login_required
@require_http_methods(["GET", "POST"])
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read.
    """
    notification_type = request.POST.get('type', 'core')
    
    try:
        if notification_type == 'core':
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        else:
            notification = get_object_or_404(TransactionNotification, id=notification_id, user=request.user)
        
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def log_social_engagement(request):
    """
    Log social engagement actions for awareness & motivation.
    """
    try:
        payload = json.loads(request.body or '{}')
        action = payload.get('action', 'activity')
        context = payload.get('context', '')
        link = payload.get('link') or ''

        title_map = {
            'share_impact': 'Impact Shared',
            'join_challenge': 'Community Challenge',
            'view_leaderboard': 'Leaderboard Viewed',
            'accept_tip': 'Sustainability Tip',
            'invite_friend': 'Invite Sent'
        }

        Notification.objects.create(
            user=request.user,
            notification_type='info',
            title=title_map.get(action, 'Community Activity'),
            message=context or 'Thanks for supporting the community goals!',
            link=link
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["GET", "POST"])
def delete_notification(request, notification_id):
    """
    Delete a notification.
    """
    notification_type = request.POST.get('type') or request.GET.get('type', 'core')
    
    try:
        if notification_type == 'core':
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        else:
            notification = get_object_or_404(TransactionNotification, id=notification_id, user=request.user)
        
        notification.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["GET", "POST"])
def mark_all_read(request):
    """
    Mark all notifications as read.
    """
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        TransactionNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

