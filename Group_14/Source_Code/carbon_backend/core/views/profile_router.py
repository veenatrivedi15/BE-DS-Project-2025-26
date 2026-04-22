from django.shortcuts import redirect

def profile_router(request):
    """
    Redirects users to the appropriate profile page based on their user type
    """
    user = request.user
    
    if user.is_employee:
        return redirect('employee_profile')
    elif user.is_employer:
        # Assuming there's an employer profile page
        return redirect('employer_dashboard')  # or employer_profile if exists
    elif user.is_bank_admin:
        # Redirect bank admins to their dashboard
        return redirect('bank_dashboard')
    elif user.is_super_admin:
        # Redirect super admins to admin dashboard
        return redirect('admin_dashboard')
    else:
        # Fallback to home page
        return redirect('home') 