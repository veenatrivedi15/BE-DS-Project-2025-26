from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, EmployerProfile, EmployeeProfile, Location

class LoginForm(AuthenticationForm):
    """Login form for users."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_email', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_password', 'placeholder': 'Password'})
    )

class EmployeeRegistrationForm(forms.Form):
    """Form for employee registration with proper employer dropdown."""
    
    # Account information
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_password'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_first_name'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_last_name'})
    )
    
    # Employer information
    employer = forms.ModelChoiceField(
        queryset=EmployerProfile.objects.filter(approved=True),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_employer'})
    )
    employee_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_employee_id'})
    )
    
    # Terms agreement
    terms = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_terms'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure we get all approved employers for the dropdown
        self.fields['employer'].queryset = EmployerProfile.objects.filter(
            approved=True
        ).order_by('company_name')
        
        # Set employer label_from_instance to display company name
        self.fields['employer'].label_from_instance = lambda obj: obj.company_name 