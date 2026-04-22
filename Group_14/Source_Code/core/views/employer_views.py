from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def is_employer(user):
    return user.is_authenticated and user.is_employer

@login_required
@user_passes_test(is_employer)
def dashboard(request):
    """
    Employer dashboard view
    """
    context = {
        'title': 'Employer Dashboard'
    }
    return render(request, 'employer/dashboard.html', context) 
from django.contrib.auth.decorators import login_required, user_passes_test

def is_employer(user):
    return user.is_authenticated and user.is_employer

@login_required
@user_passes_test(is_employer)
def dashboard(request):
    """
    Employer dashboard view
    """
    context = {
        'title': 'Employer Dashboard'
    }
    return render(request, 'employer/dashboard.html', context) 