from django.shortcuts import render
from users.models import EmployerProfile

def register_hub(request):
    """
    View for the registration hub page
    """
    # Get all approved employers for the dropdown
    approved_employers = EmployerProfile.objects.filter(approved=True).order_by('company_name')
    
    return render(request, 'auth/register.html', {
        'employers': approved_employers
    }) 