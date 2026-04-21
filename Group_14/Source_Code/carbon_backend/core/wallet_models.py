"""
Digital Carbon Credit & Wallet System Models
Handles credit creation, wallet management, and transactions
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

CustomUser = get_user_model()

class CarbonWallet(models.Model):
    """Digital wallet for storing carbon credits"""
    
    WALLET_TYPES = [
        ('employee', 'Employee Wallet'),
        ('employer', 'Employer Wallet'),
        ('system', 'System Wallet'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='carbon_wallets')
    wallet_type = models.CharField(max_length=20, choices=WALLET_TYPES, default='employee')
    balance = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, 
                               validators=[MinValueValidator(0)])
    available_balance = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000,
                                         validators=[MinValueValidator(0)])
    frozen_balance = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000,
                                      validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carbon_wallets'
        verbose_name = 'Carbon Wallet'
        verbose_name_plural = 'Carbon Wallets'
        
    def __str__(self):
        return f"{self.owner.email} - {self.wallet_type} Wallet ({self.balance} credits)"
    
    def add_credits(self, amount, source=None, description=None):
        """Add credits to wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += Decimal(str(amount))
        self.available_balance += Decimal(str(amount))
        self.save()
        
        # Create transaction record
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            source=source,
            description=description,
            balance_after=self.balance
        )
    
    def freeze_credits(self, amount, reason=None):
        """Freeze credits (e.g., for pending transactions)"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < amount:
            raise ValueError("Insufficient available credits")
        
        self.available_balance -= Decimal(str(amount))
        self.frozen_balance += Decimal(str(amount))
        self.save()
        
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='freeze',
            amount=amount,
            description=reason,
            balance_after=self.balance
        )
    
    def unfreeze_credits(self, amount, reason=None):
        """Unfreeze credits"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.frozen_balance < amount:
            raise ValueError("Insufficient frozen credits")
        
        self.frozen_balance -= Decimal(str(amount))
        self.available_balance += Decimal(str(amount))
        self.save()
        
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='unfreeze',
            amount=amount,
            description=reason,
            balance_after=self.balance
        )
    
    def deduct_credits(self, amount, destination=None, description=None):
        """Deduct credits from wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < amount:
            raise ValueError("Insufficient available credits")
        
        self.available_balance -= Decimal(str(amount))
        self.balance -= Decimal(str(amount))
        self.save()
        
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            amount=-amount,
            destination=destination,
            description=description,
            balance_after=self.balance
        )

class WalletTransaction(models.Model):
    """Transaction history for carbon wallets"""
    
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('freeze', 'Freeze'),
        ('unfreeze', 'Unfreeze'),
        ('transfer_out', 'Transfer Out'),
        ('transfer_in', 'Transfer In'),
        ('expiry', 'Expiry'),
        ('reward', 'Reward'),
        ('penalty', 'Penalty'),
    ]
    
    SOURCES = [
        ('trip', 'Trip Activity'),
        ('transfer', 'Transfer'),
        ('reward', 'Reward'),
        ('penalty', 'Penalty'),
        ('expiry', 'Credit Expiry'),
        ('system', 'System Adjustment'),
        ('marketplace', 'Marketplace'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(CarbonWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    source = models.CharField(max_length=50, choices=SOURCES, null=True, blank=True)
    source_id = models.CharField(max_length=100, null=True, blank=True)  # ID of related object
    destination = models.CharField(max_length=200, null=True, blank=True)  # Destination wallet/user
    description = models.TextField(null=True, blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=4)
    transaction_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)  # Blockchain hash
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wallet_transactions'
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.wallet.owner.email} - {self.transaction_type} {self.amount} credits"
    
    def save(self, *args, **kwargs):
        # Generate transaction hash if not provided
        if not self.transaction_hash:
            import hashlib
            import time
            hash_data = f"{self.wallet.id}{self.transaction_type}{self.amount}{time.time()}"
            self.transaction_hash = hashlib.sha256(hash_data.encode()).hexdigest()
        super().save(*args, **kwargs)

class CreditTransfer(models.Model):
    """Credit transfer between wallets"""
    
    TRANSFER_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_wallet = models.ForeignKey(CarbonWallet, on_delete=models.CASCADE, related_name='sent_transfers')
    to_wallet = models.ForeignKey(CarbonWallet, on_delete=models.CASCADE, related_name='received_transfers')
    amount = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(0.0001)])
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS, default='pending')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'credit_transfers'
        verbose_name = 'Credit Transfer'
        verbose_name_plural = 'Credit Transfers'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Transfer: {self.from_wallet.owner.email} → {self.to_wallet.owner.email} ({self.amount} credits)"
    
    def execute_transfer(self):
        """Execute the credit transfer"""
        try:
            if self.status != 'pending':
                raise ValueError("Transfer is not in pending status")
            
            # Freeze credits from sender
            self.from_wallet.freeze_credits(self.amount, f"Transfer to {self.to_wallet.owner.email}")
            
            # Deduct from sender
            self.from_wallet.deduct_credits(self.amount, self.to_wallet.owner.email, self.message)
            
            # Add to receiver
            self.to_wallet.add_credits(self.amount, 'transfer', f"Transfer from {self.from_wallet.owner.email}: {self.message}")
            
            # Update status
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.failure_reason = str(e)
            self.save()
            
            # Unfreeze credits if transfer failed
            try:
                self.from_wallet.unfreeze_credits(self.amount, f"Failed transfer: {str(e)}")
            except:
                pass
            
            return False

class CreditExpiry(models.Model):
    """Credit expiry management"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(CarbonWallet, on_delete=models.CASCADE, related_name='expiry_records')
    amount = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(0.0001)])
    expiry_date = models.DateTimeField()
    is_expired = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'credit_expiry'
        verbose_name = 'Credit Expiry'
        verbose_name_plural = 'Credit Expiries'
        ordering = ['expiry_date']
        
    def __str__(self):
        return f"{self.wallet.owner.email} - {self.amount} credits expire on {self.expiry_date}"
    
    def process_expiry(self):
        """Process credit expiry"""
        if self.processed or self.is_expired:
            return False
        
        # Deduct expired credits
        if self.wallet.balance >= self.amount:
            self.wallet.deduct_credits(self.amount, description=f"Credit expiry on {self.expiry_date}")
            self.is_expired = True
            self.processed = True
            self.processed_at = timezone.now()
            self.save()
            return True
        
        return False

class WalletSettings(models.Model):
    """Wallet configuration settings"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.OneToOneField(CarbonWallet, on_delete=models.CASCADE, related_name='settings')
    auto_transfer_enabled = models.BooleanField(default=False)
    auto_transfer_threshold = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000)
    auto_transfer_recipient = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    notification_enabled = models.BooleanField(default=True)
    low_balance_alert = models.DecimalField(max_digits=12, decimal_places=4, default=10.0000)
    monthly_report_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wallet_settings'
        verbose_name = 'Wallet Settings'
        verbose_name_plural = 'Wallet Settings'
        
    def __str__(self):
        return f"Settings for {self.wallet.owner.email}"
