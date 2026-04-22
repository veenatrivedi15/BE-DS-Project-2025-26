from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CustomUser(AbstractUser):
    """Custom user model with role flags for different user types."""
    
    # User role flags
    is_employee = models.BooleanField(default=False)
    is_employer = models.BooleanField(default=False)
    is_bank_admin = models.BooleanField(default=False)
    is_super_admin = models.BooleanField(default=False)
    
    # Additional fields
    email = models.EmailField(_('email address'), unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    approved = models.BooleanField(default=False)
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.email

    def get_role(self):
        """Return the user's primary role."""
        if self.is_super_admin:
            return 'super_admin'
        elif self.is_bank_admin:
            return 'bank_admin'
        elif self.is_employer:
            return 'employer'
        elif self.is_employee:
            return 'employee'
        else:
            return 'unknown'

    def is_approved_role(self):
        """Check if the user is approved for their role."""
        if self.is_super_admin or self.is_bank_admin:
            # Admins are automatically approved
            return True
        elif self.is_employer:
            try:
                return self.employer_profile.approved
            except:
                return False
        elif self.is_employee:
            try:
                return self.employee_profile.approved
            except:
                return False
        return False

    def can_approve_users(self):
        """Check if the user can approve other users."""
        return self.is_super_admin or self.is_bank_admin or self.is_employer

    def can_access_admin(self):
        """Check if the user can access the admin panel."""
        return self.is_superuser or self.is_staff


class EmployerProfile(models.Model):
    """Profile for employers with company details."""
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='employer_profile'
    )
    company_name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    industry = models.CharField(max_length=100)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    initial_credits_allocated = models.BooleanField(default=False)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return self.company_name


class EmployeeProfile(models.Model):
    """Profile for employees with employment details."""
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='employee_profile'
    )
    employer = models.ForeignKey(
        EmployerProfile, 
        on_delete=models.CASCADE, 
        related_name='employees'
    )
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    department = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.user.email} ({self.employer.company_name})"


class Location(models.Model):
    """Model for storing geographic locations."""
    
    LOCATION_TYPES = (
        ('home', 'Home'),
        ('office', 'Office'),
        ('commute', 'Commute'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100, default='', blank=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='locations'
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    address = models.CharField(max_length=255)
    location_type = models.CharField(max_length=10, choices=LOCATION_TYPES, default='other')
    employer = models.ForeignKey(
        EmployerProfile, 
        on_delete=models.CASCADE, 
        related_name='office_locations',
        null=True,
        blank=True
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        if self.name:
            return self.name
        return f"{self.location_type}: {self.address[:30]}"
    
    def save(self, *args, **kwargs):
        # Generate a name if not provided
        if not self.name:
            if self.location_type == 'home':
                self.name = f"Home - {self.created_by.get_full_name()}"
            elif self.location_type == 'office':
                if self.employer:
                    self.name = f"Office - {self.employer.company_name}"
                else:
                    self.name = f"Office - {self.address[:20]}"
            else:
                self.name = f"{self.location_type.capitalize()} - {self.address[:20]}"
        
        super().save(*args, **kwargs)


class EmployeeInvitation(models.Model):
    """Model for tracking employee invitations sent by employers."""
    
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    email = models.EmailField()
    department = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Invitation for {self.email} from {self.employer.company_name}"
    
    def is_valid(self):
        """Check if the invitation is still valid."""
        return not self.is_used and self.expires_at > timezone.now()
