from django.urls import path
from core.views.notification_views import (
    get_notifications,
    mark_notification_read,
    delete_notification,
    mark_all_read,
    log_social_engagement
)

urlpatterns = [
    path('', get_notifications, name='get_notifications'),
    path('<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('<int:notification_id>/delete/', delete_notification, name='delete_notification'),
    path('mark-all-read/', mark_all_read, name='mark_all_read'),
    path('social-engagement/', log_social_engagement, name='log_social_engagement'),
]



