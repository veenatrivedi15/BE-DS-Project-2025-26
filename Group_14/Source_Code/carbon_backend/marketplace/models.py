from django.db import models
from django.utils import timezone
from users.models import CustomUser, EmployerProfile, EmployeeProfile


class MarketOffer(models.Model):
    """Model for carbon credit market offers."""
    
    OFFER_STATUS = (
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    seller = models.ForeignKey(
        EmployerProfile, 
        on_delete=models.CASCADE,
        related_name='market_offers'
    )
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_credit = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=OFFER_STATUS, default='active')
    
    def __str__(self):
        return f"{self.credit_amount} credits at ${self.price_per_credit}/credit by {self.seller.company_name}"


class MarketplaceTransaction(models.Model):
    """Model for tracking marketplace transactions."""
    
    TRANSACTION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    offer = models.ForeignKey(
        MarketOffer,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True
    )
    seller = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name='sold_transactions'
    )
    buyer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name='purchased_transactions'
    )
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS, default='pending')
    admin_approval_required = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.credit_amount} credits for ${self.total_price} ({self.get_status_display()})"


class TransactionNotification(models.Model):
    """Model for marketplace transaction notifications."""
    
    NOTIFICATION_TYPES = (
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('offer', 'Offer'),
        ('status_change', 'Status Change'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='marketplace_notifications'
    )
    transaction = models.ForeignKey(
        MarketplaceTransaction,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    notification_type = models.CharField(max_length=15, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.notification_type} notification for {self.user.email}"


class EmployeeCreditOffer(models.Model):
    """Model for employee-to-employer credit offers."""
    
    OFFER_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    OFFER_TYPE = (
        ('buy', 'Buy Credits'),
        ('sell', 'Sell Credits'),
        ('redeem', 'Redeem Credits'),
    )
    
    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='credit_offers'
    )
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name='employee_credit_offers'
    )
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPE)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    market_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Current market rate when offer was created")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total dollar amount of the transaction")
    status = models.CharField(max_length=10, choices=OFFER_STATUS, default='pending')
    additional_info = models.TextField(blank=True, null=True, help_text="Additional information for redemption requests")
    created_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        action = "buy" if self.offer_type == 'buy' else "sell"
        return f"{self.employee.user.get_full_name()} wants to {action} {self.credit_amount} credits for ${self.total_amount}"


# Signal handlers for transaction status changes
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=MarketplaceTransaction)
def create_transaction_notifications(sender, instance, created, **kwargs):
    """Create notifications when transaction status changes."""
    if created:
        # New transaction created
        # Notify seller about new pending transaction
        TransactionNotification.objects.create(
            transaction=instance,
            user=instance.seller.user,
            message=f"New transaction #{instance.id}: {instance.buyer.company_name} wants to buy {instance.credit_amount} credits for ${instance.total_price}."
        )
        
        # Notify bank admins about pending approval
        bank_admins = CustomUser.objects.filter(is_bank_admin=True)
        for admin in bank_admins:
            TransactionNotification.objects.create(
                transaction=instance,
                user=admin,
                message=f"Transaction #{instance.id} requires your approval: {instance.buyer.company_name} buying {instance.credit_amount} credits from {instance.seller.company_name}."
            )
    
    elif not created and instance.status in ['completed', 'rejected', 'cancelled']:
        # Status changed to completed, rejected or cancelled
        # Notify buyer
        TransactionNotification.objects.create(
            transaction=instance,
            user=instance.buyer.user,
            message=f"Transaction #{instance.id} has been {instance.status}. {instance.credit_amount} credits purchase from {instance.seller.company_name} for ${instance.total_price}."
        )
        
        # Notify seller
        TransactionNotification.objects.create(
            transaction=instance,
            user=instance.seller.user,
            message=f"Transaction #{instance.id} has been {instance.status}. Sale of {instance.credit_amount} credits to {instance.buyer.company_name} for ${instance.total_price}."
        )
