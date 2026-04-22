from rest_framework import serializers
from .models import Trip, CarbonCredit
from users.models import Location, EmployeeProfile
from django.conf import settings
import googlemaps
from datetime import datetime

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'latitude', 'longitude']

class TripSerializer(serializers.ModelSerializer):
    """Serializer for Trip model."""
    
    start_location_name = serializers.CharField(source='start_location.name', read_only=True)
    end_location_name = serializers.CharField(source='end_location.name', read_only=True, default='')
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Trip
        fields = [
            'id', 'employee', 'employee_name', 
            'start_location', 'start_location_name',
            'end_location', 'end_location_name',
            'start_time', 'end_time', 'transport_mode',
            'distance_km', 'carbon_savings', 'credits_earned',
            'proof_image', 'verification_status', 'verified_by',
            'created_at', 'duration'
        ]
        read_only_fields = [
            'carbon_savings', 'credits_earned', 'verified_by',
            'verification_status'
        ]
    
    def get_duration(self, obj):
        """Get the duration of the trip as a string."""
        duration = obj.duration
        if duration:
            # Format duration as hours and minutes
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return None


class TripStartSerializer(serializers.Serializer):
    """Serializer for starting a trip."""
    
    start_location = serializers.CharField(max_length=255)
    start_address = serializers.CharField(max_length=255, required=False)
    start_latitude = serializers.FloatField(required=False)
    start_longitude = serializers.FloatField(required=False)
    transport_mode = serializers.ChoiceField(choices=Trip.TRANSPORT_MODES)
    
    def validate(self, data):
        """
        Validate the start location data.
        If GPS coordinates are provided, reverse geocode to get the address.
        """
        # If GPS coordinates are provided but no address
        if ('start_latitude' in data and 'start_longitude' in data and 
            not data.get('start_address')):
            
            # Try to reverse geocode the coordinates
            try:
                gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                reverse_geocode_result = gmaps.reverse_geocode(
                    (data['start_latitude'], data['start_longitude'])
                )
                if reverse_geocode_result:
                    formatted_address = reverse_geocode_result[0].get('formatted_address', '')
                    data['start_address'] = formatted_address
            except Exception as e:
                # If reverse geocoding fails, just continue with the coordinates
                pass
        
        return data


class TripEndSerializer(serializers.Serializer):
    """Serializer for ending a trip."""
    
    end_location = serializers.CharField(max_length=255)
    end_address = serializers.CharField(max_length=255, required=False)
    end_latitude = serializers.FloatField(required=False)
    end_longitude = serializers.FloatField(required=False)
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    
    def validate(self, data):
        """
        Validate the end location data.
        If GPS coordinates are provided, reverse geocode to get the address.
        If distance is not provided, calculate it based on start and end locations.
        """
        # If GPS coordinates are provided but no address
        if ('end_latitude' in data and 'end_longitude' in data and 
            not data.get('end_address')):
            
            # Try to reverse geocode the coordinates
            try:
                gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                reverse_geocode_result = gmaps.reverse_geocode(
                    (data['end_latitude'], data['end_longitude'])
                )
                if reverse_geocode_result:
                    formatted_address = reverse_geocode_result[0].get('formatted_address', '')
                    data['end_address'] = formatted_address
            except Exception as e:
                # If reverse geocoding fails, just continue with the coordinates
                pass
        
        # If distance is not provided and we have a trip ID and start/end coordinates
        trip = self.context.get('trip')
        if 'distance_km' not in data and trip and trip.start_location:
            if ('end_latitude' in data and 'end_longitude' in data and 
                hasattr(trip.start_location, 'latitude') and 
                hasattr(trip.start_location, 'longitude')):
                
                try:
                    # Calculate distance using Google Maps API
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    directions_result = gmaps.directions(
                        (trip.start_location.latitude, trip.start_location.longitude),
                        (data['end_latitude'], data['end_longitude']),
                        mode=trip.transport_mode if trip.transport_mode in ['driving', 'walking', 'bicycling', 'transit'] else 'driving',
                        departure_time=datetime.now()
                    )
                    
                    if directions_result:
                        # Get distance in meters and convert to kilometers
                        distance_meters = directions_result[0]['legs'][0]['distance']['value']
                        data['distance_km'] = round(distance_meters / 1000, 2)
                except Exception as e:
                    # If distance calculation fails, ask for manual distance
                    pass
                
        return data


class TripVerificationSerializer(serializers.Serializer):
    """Serializer for verifying a trip."""
    
    verification_status = serializers.ChoiceField(choices=Trip.VERIFICATION_STATUS)
    verification_notes = serializers.CharField(max_length=500, required=False)


class CarbonCreditSerializer(serializers.ModelSerializer):
    """Serializer for the CarbonCredit model."""
    
    trip_date = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CarbonCredit
        fields = [
            'id', 'amount', 'source_trip', 'owner_type', 
            'owner_id', 'timestamp', 'status', 
            'expiry_date', 'trip_date', 'owner_name'
        ]
    
    def get_trip_date(self, obj):
        """Get the date of the source trip."""
        if obj.source_trip:
            return obj.source_trip.start_time.date()
        return None
    
    def get_owner_name(self, obj):
        """Get the name of the credit owner."""
        if obj.owner_type == 'employee':
            try:
                employee = EmployeeProfile.objects.get(id=obj.owner_id)
                return employee.user.get_full_name()
            except EmployeeProfile.DoesNotExist:
                return f"Employee #{obj.owner_id}"
        else:
            # For employers, we would need similar logic
            return f"Employer #{obj.owner_id}"


class TripStatsSerializer(serializers.Serializer):
    """Serializer for trip statistics."""
    
    total_trips = serializers.IntegerField()
    total_distance = serializers.FloatField()
    total_carbon_saved = serializers.FloatField()
    total_credits_earned = serializers.FloatField()
    trips_by_mode = serializers.DictField(child=serializers.IntegerField())
    verified_trips = serializers.IntegerField()
    rejected_trips = serializers.IntegerField()
    pending_trips = serializers.IntegerField()


class CreditStatsSerializer(serializers.Serializer):
    """Serializer for credit statistics."""
    
    total_credits_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_credits = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_credits = serializers.DecimalField(max_digits=10, decimal_places=2)
    expired_credits = serializers.DecimalField(max_digits=10, decimal_places=2)
    used_credits = serializers.DecimalField(max_digits=10, decimal_places=2)


class EmployerCreditStatsSerializer(serializers.Serializer):
    """Serializer for employer credit statistics."""
    
    total_credits_issued = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_credits = serializers.DecimalField(max_digits=10, decimal_places=2)
    credits_by_status = serializers.DictField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2)
    )
    top_employees = serializers.ListField(child=serializers.DictField()) 