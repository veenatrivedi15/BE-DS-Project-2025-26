from rest_framework import serializers
from .models import CustomUser, EmployerProfile, EmployeeProfile, Location


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the CustomUser model."""
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 
                  'is_employee', 'is_employer', 'is_bank_admin', 'is_super_admin',
                  'approved', 'date_joined']
        read_only_fields = ['id', 'date_joined', 'approved', 
                           'is_employee', 'is_employer', 'is_bank_admin', 'is_super_admin']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }
    
    def create(self, validated_data):
        """Create and return a new user."""
        user = CustomUser.objects.create_user(**validated_data)
        return user


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for the Location model."""
    
    class Meta:
        model = Location
        fields = ['id', 'created_by', 'latitude', 'longitude', 'address',
                  'location_type', 'employer', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class EmployerProfileSerializer(serializers.ModelSerializer):
    """Serializer for the EmployerProfile model."""
    
    user = UserSerializer(read_only=True)
    office_locations = LocationSerializer(many=True, read_only=True)
    
    class Meta:
        model = EmployerProfile
        fields = ['id', 'user', 'company_name', 'registration_number', 
                  'industry', 'approved', 'created_at', 'office_locations']
        read_only_fields = ['id', 'user', 'approved', 'created_at']


class EmployeeProfileSerializer(serializers.ModelSerializer):
    """Serializer for the EmployeeProfile model."""
    
    user = UserSerializer(read_only=True)
    employer = EmployerProfileSerializer(read_only=True)
    
    class Meta:
        model = EmployeeProfile
        fields = ['id', 'user', 'employer', 'employee_id', 'approved', 'created_at', 'wallet_balance', 'department']
        read_only_fields = ['id', 'user', 'approved', 'created_at']


class EmployerRegistrationSerializer(serializers.Serializer):
    """Serializer for employer registration."""
    
    # User fields
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    
    # Employer profile fields
    company_name = serializers.CharField(max_length=100)
    registration_number = serializers.CharField(max_length=50)
    industry = serializers.CharField(max_length=100)

    def validate_username(self, value):
        """Validate that the username is not already taken."""
        # Check if user exists with this username
        existing_user = CustomUser.objects.filter(username=value).first()
        if existing_user:
            # Allow updating own username (for existing users)
            email = self.initial_data.get('email')
            if email and existing_user.email == email:
                return value
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_registration_number(self, value):
        """Validate that the registration number is not already taken."""
        existing_employer = EmployerProfile.objects.filter(registration_number=value).first()
        if existing_employer:
            raise serializers.ValidationError("This registration number is already registered.")
        return value


class EmployeeRegistrationSerializer(serializers.Serializer):
    """Serializer for employee registration."""
    
    # User fields
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    
    # Employee profile fields
    employer_id = serializers.IntegerField()
    employee_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_username(self, value):
        """Validate that the username is not already taken."""
        # Check if user exists with this username
        existing_user = CustomUser.objects.filter(username=value).first()
        if existing_user:
            # Allow updating own username (for existing users)
            email = self.initial_data.get('email')
            if email and existing_user.email == email:
                return value
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_employer_id(self, value):
        """Validate that the employer exists and is approved."""
        try:
            employer = EmployerProfile.objects.get(id=value)
            if not employer.approved:
                raise serializers.ValidationError("Selected employer is not approved yet.")
            return value
        except EmployerProfile.DoesNotExist:
            raise serializers.ValidationError("Selected employer does not exist.") 