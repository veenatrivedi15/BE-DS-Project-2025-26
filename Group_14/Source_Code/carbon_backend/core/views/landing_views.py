from django.shortcuts import render, redirect

def landing_page(request):
    """
    View function for the landing page
    """
    if request.user.is_authenticated:
        return redirect('dashboard_router')
    return render(request, 'landing.html')

def dashboard_router(request):
    """
    Routes users to the appropriate dashboard based on their role
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.user.is_super_admin:
        return redirect('admin_dashboard:admin_dashboard')
    elif request.user.is_bank_admin:
        return redirect('bank:bank_dashboard')
    elif request.user.is_employer:
        return redirect('employer:employer_dashboard')
    elif request.user.is_employee:
        return redirect('employee:employee_dashboard')
    else:
        # Default fallback
        return redirect('home') 