"""
Pollution and Industrial Zone Models for Location Awareness
"""
from django.db import models
from django.utils import timezone
from users.models import CustomUser, Location
from decimal import Decimal


class IndustrialZone(models.Model):
    """Model for storing industrial zone locations and data."""
    
    ZONE_TYPES = (
        ('heavy_industry', 'Heavy Industry'),
        ('manufacturing', 'Manufacturing'),
        ('power_plant', 'Power Plant'),
        ('chemical', 'Chemical Plant'),
        ('steel', 'Steel Plant'),
        ('textile', 'Textile Industry'),
        ('other', 'Other Industrial'),
    )
    
    name = models.CharField(max_length=200)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    emission_intensity = models.DecimalField(
        max_digits=8, 
        decimal_places=4,
        help_text="CO2 emission intensity in tons per year"
    )
    operating_hours = models.JSONField(
        default=dict,
        help_text="Operating hours {'start': '08:00', 'end': '18:00', 'days': [1,2,3,4,5]}"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"
    
    def is_active_now(self):
        """Check if the industrial zone is currently active."""
        if not self.is_active or not self.operating_hours:
            return False
        
        now = timezone.now()
        current_hour = now.hour
        current_weekday = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check if current day is in operating days
        operating_days = self.operating_hours.get('days', [])
        if current_weekday not in operating_days:
            return False
        
        # Check if current time is within operating hours
        start_hour = int(self.operating_hours.get('start', '00:00').split(':')[0])
        end_hour = int(self.operating_hours.get('end', '23:59').split(':')[0])
        
        return start_hour <= current_hour <= end_hour


class PollutionData(models.Model):
    """Model for storing real-time pollution data."""
    
    POLLUTANTS = (
        ('pm25', 'PM2.5'),
        ('pm10', 'PM10'),
        ('co', 'Carbon Monoxide'),
        ('no2', 'Nitrogen Dioxide'),
        ('so2', 'Sulfur Dioxide'),
        ('o3', 'Ozone'),
        ('aqi', 'Air Quality Index'),
    )
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='pollution_data'
    )
    pollutant_type = models.CharField(max_length=10, choices=POLLUTANTS)
    value = models.DecimalField(max_digits=8, decimal_places=4)
    unit = models.CharField(max_length=20, default='μg/m³')
    aqi_level = models.CharField(
        max_length=20,
        choices=(
            ('good', 'Good (0-50)'),
            ('moderate', 'Moderate (51-100)'),
            ('unhealthy_sensitive', 'Unhealthy for Sensitive (101-150)'),
            ('unhealthy', 'Unhealthy (151-200)'),
            ('very_unhealthy', 'Very Unhealthy (201-300)'),
            ('hazardous', 'Hazardous (301+)'),
        ),
        default='moderate'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=100, default='API')
    
    class Meta:
        indexes = [
            models.Index(fields=['location', 'pollutant_type', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.location.address}: {self.pollutant_type} = {self.value} {self.unit}"


class UserPollutionAlert(models.Model):
    """Model for storing user-specific pollution alerts."""
    
    ALERT_TYPES = (
        ('high_pollution', 'High Pollution Alert'),
        ('industrial_activity', 'Industrial Activity Alert'),
        ('air_quality', 'Air Quality Warning'),
        ('health_advisory', 'Health Advisory'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='pollution_alerts'
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    industrial_zone = models.ForeignKey(
        IndustrialZone,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    severity = models.CharField(
        max_length=10,
        choices=(
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ),
        default='medium'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def is_expired(self):
        """Check if the alert has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class PollutionImpact(models.Model):
    """Model for calculating and storing pollution impact comparisons."""
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='pollution_impacts'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE
    )
    carbon_savings_kg = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Carbon savings in kg CO2"
    )
    equivalent_factory_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Equivalent factory operation hours offset"
    )
    trees_planted_equivalent = models.IntegerField(
        help_text="Number of trees equivalent to the carbon savings"
    )
    cars_off_road_equivalent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Number of cars taken off road for a day"
    )
    calculation_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-calculation_date']
    
    def __str__(self):
        return f"{self.user.email}: {self.carbon_savings_kg}kg CO2 saved"


class EnvironmentalMetric(models.Model):
    """Model for storing environmental conversion metrics."""
    
    metric_name = models.CharField(max_length=100, unique=True)
    co2_kg_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="CO2 kg equivalent per unit"
    )
    description = models.TextField(blank=True)
    source = models.CharField(max_length=100, default='IPCC 2006')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.metric_name}: {self.co2_kg_per_unit} kg CO2/unit"
