from django.db import models
from django.utils import timezone

class SystemConfig(models.Model):
    """Model for storing system-wide configuration settings."""
    name = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_value(cls, name, default=None):
        """Get a configuration value by name."""
        try:
            config = cls.objects.get(name=name, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default

class Notification(models.Model):
    """Model for user notifications."""
    
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('redemption', 'Redemption Request'),
        ('trip', 'Trip Update'),
        ('credit', 'Credit Update'),
        ('system', 'System'),
    )
    
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    link = models.URLField(blank=True, null=True, help_text="Optional link to related page")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email} ({'Read' if self.is_read else 'Unread'})"
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])
