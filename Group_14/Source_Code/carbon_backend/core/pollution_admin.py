from django.contrib import admin
from .pollution_models import (
    IndustrialZone, PollutionData, UserPollutionAlert, 
    PollutionImpact, EnvironmentalMetric
)


@admin.register(IndustrialZone)
class IndustrialZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'zone_type', 'latitude', 'longitude', 'emission_intensity', 'is_active']
    list_filter = ['zone_type', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at']


@admin.register(PollutionData)
class PollutionDataAdmin(admin.ModelAdmin):
    list_display = ['location', 'pollutant_type', 'value', 'unit', 'aqi_level', 'timestamp', 'source']
    list_filter = ['pollutant_type', 'aqi_level', 'source']
    search_fields = ['location__address']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']


@admin.register(UserPollutionAlert)
class UserPollutionAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'title', 'severity', 'is_read', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_read']
    search_fields = ['user__email', 'title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(PollutionImpact)
class PollutionImpactAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'carbon_savings_kg', 'equivalent_factory_hours', 'trees_planted_equivalent', 'calculation_date']
    list_filter = ['calculation_date']
    search_fields = ['user__email', 'location__address']
    readonly_fields = ['calculation_date']
    ordering = ['-calculation_date']


@admin.register(EnvironmentalMetric)
class EnvironmentalMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'co2_kg_per_unit', 'source', 'is_active']
    list_filter = ['is_active', 'source']
    search_fields = ['metric_name']
    readonly_fields = ['created_at']
