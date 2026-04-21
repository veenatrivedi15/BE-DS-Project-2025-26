from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

def bank_required(function):
    """
    Decorator for views that checks that the logged in user is a bank admin,
    redirecting to the login page if necessary.
    """
    def check_user(user):
        return user.is_authenticated and user.is_bank_admin
    
    decorator = user_passes_test(check_user, login_url='login')
    return decorator(function)

def employer_required(function):
    """
    Decorator for views that checks that the logged in user is an employer,
    redirecting to the login page if necessary.
    """
    def check_user(user):
        return user.is_authenticated and user.is_employer
    
    decorator = user_passes_test(check_user, login_url='login')
    return decorator(function)

def employee_required(function):
    """
    Decorator for views that checks that the logged in user is an employee,
    redirecting to the login page if necessary.
    """
    def check_user(user):
        return user.is_authenticated and user.is_employee
    
    decorator = user_passes_test(check_user, login_url='login')
    return decorator(function)

def super_admin_required(function):
    """
    Decorator for views that checks that the logged in user is a super admin,
    redirecting to the login page if necessary.
    """
    def check_user(user):
        return user.is_authenticated and user.is_super_admin
    
    decorator = user_passes_test(check_user, login_url='login')
    return decorator(function) 