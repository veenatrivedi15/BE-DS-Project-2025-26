from django.db import models
from django.utils import timezone
from users.models import CustomUser, EmployeeProfile, Location


class Trip(models.Model):
    """Model for tracking employee trips."""
    
    TRANSPORT_MODES = (
        ('car', 'Car (Single Occupancy)'),
        ('carpool', 'Carpool'),
        ('two_wheeler_single', 'Two Wheeler (Solo)'),
        ('two_wheeler_double', 'Two Wheeler (Carpool - 2 persons)'),
        ('public_transport', 'Public Transport'),
        ('bicycle', 'Bicycle'),
        ('walking', 'Walking'),
        ('work_from_home', 'Work From Home'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    )
    
    employee = models.ForeignKey(
        EmployeeProfile, 
        on_delete=models.CASCADE, 
        related_name='trips'
    )
    start_location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        related_name='trip_starts',
        null=True
    )
    end_location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        related_name='trip_ends',
        null=True
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    transport_mode = models.CharField(
        max_length=20, 
        choices=TRANSPORT_MODES
    )
    distance_km = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        null=True,
        blank=True
    )
    carbon_savings = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        null=True,
        blank=True
    )
    credits_earned = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        null=True,
        blank=True
    )
    proof_image = models.ImageField(
        upload_to='trip_proofs/',
        null=True,
        blank=True
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='verified_trips',
        null=True,
        blank=True
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated travel time in minutes based on transport mode and distance"
    )
    
    # Enhanced calculation fields (WRI 2015 + IPCC 2006)
    ef_baseline = models.FloatField(
        null=True,
        blank=True,
        help_text="Baseline emission factor (kg CO₂/km)"
    )
    ef_actual = models.FloatField(
        null=True,
        blank=True,
        help_text="Actual emission factor (kg CO₂/km)"
    )
    emission_difference = models.FloatField(
        null=True,
        blank=True,
        help_text="Emission difference (kg CO₂/km)"
    )
    time_period = models.CharField(
        max_length=20,
        choices=(
            ('peak_morning', 'Peak Morning (7-10 AM)'),
            ('peak_evening', 'Peak Evening (6-9 PM)'),
            ('off_peak', 'Off-Peak'),
            ('late_night', 'Late Night (11 PM - 5 AM)'),
        ),
        default='off_peak',
        null=True,
        blank=True
    )
    traffic_condition = models.CharField(
        max_length=20,
        choices=(
            ('heavy', 'Heavy'),
            ('moderate', 'Moderate'),
            ('light', 'Light'),
        ),
        default='moderate',
        null=True,
        blank=True
    )
    weather_condition = models.CharField(
        max_length=20,
        choices=(
            ('heavy_rain', 'Heavy Rain'),
            ('light_rain', 'Light Rain'),
            ('normal', 'Normal'),
            ('favorable', 'Favorable'),
        ),
        default='normal',
        null=True,
        blank=True
    )
    route_type = models.CharField(
        max_length=20,
        choices=(
            ('hilly', 'Hilly/Uphill'),
            ('city_center', 'City Center'),
            ('highway', 'Highway'),
            ('suburban', 'Suburban'),
        ),
        default='suburban',
        null=True,
        blank=True
    )
    aqi_level = models.CharField(
        max_length=20,
        choices=(
            ('hazardous', 'Hazardous (>300)'),
            ('very_poor', 'Very Poor (201-300)'),
            ('moderate', 'Moderate (101-200)'),
            ('good', 'Good (<100)'),
        ),
        default='moderate',
        null=True,
        blank=True
    )
    season = models.CharField(
        max_length=20,
        choices=(
            ('winter', 'Winter'),
            ('summer', 'Summer'),
            ('monsoon', 'Monsoon'),
            ('post_monsoon', 'Post-Monsoon'),
        ),
        default='post_monsoon',
        null=True,
        blank=True
    )
    time_weight = models.FloatField(
        null=True,
        blank=True,
        help_text="Time weight factor"
    )
    context_factor = models.FloatField(
        null=True,
        blank=True,
        help_text="Context factor (Weather × Route × AQI × Load × Seasonal)"
    )
    carbon_credits_earned = models.FloatField(
        null=True,
        blank=True,
        help_text="Carbon credits earned (kg CO₂) - calculated using formula or ML"
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=(
            ('formula', 'Formula-based'),
            ('ml', 'ML Prediction'),
            ('hybrid', 'Hybrid (ML + Formula)'),
        ),
        default='formula',
        null=True,
        blank=True
    )
    ml_prediction_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="ML model prediction confidence (0-1)"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.employee.user.email}: {self.start_time} ({self.transport_mode})"
    
    @property
    def duration(self):
        """Calculate the duration of the trip."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


class CarbonCredit(models.Model):
    """Model for tracking carbon credits."""
    
    CREDIT_STATUS = (
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source_trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        related_name='generated_credits',
        null=True,
        blank=True
    )
    owner_type = models.CharField(
        max_length=10,
        choices=(('employee', 'Employee'), ('employer', 'Employer'))
    )
    owner_id = models.IntegerField()  # ID of either EmployeeProfile or EmployerProfile
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10,
        choices=CREDIT_STATUS,
        default='active'
    )
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.amount} credits for {self.owner_type} ({self.owner_id})"
