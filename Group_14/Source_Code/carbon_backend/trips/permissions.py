from rest_framework import permissions
from users.models import EmployeeProfile, EmployerProfile

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of a trip or admins to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any trip
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Check if the trip belongs to the employee user
        if hasattr(obj, 'employee') and hasattr(request.user, 'employee_profile'):
            return obj.employee == request.user.employee_profile
            
        # Check if the trip belongs to an employee of the employer user
        if hasattr(obj, 'employee') and hasattr(request.user, 'employer_profile'):
            return obj.employee.employer == request.user.employer_profile
            
        return False


class IsEmployerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow employers or admins to access the view.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.is_employer or request.user.is_super_admin or request.user.is_bank_admin)
        )
    
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any object
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # For credit stats, check if the employer owns them
        if hasattr(obj, 'owner_type') and obj.owner_type == 'employer':
            if hasattr(request.user, 'employer_profile'):
                return obj.owner_id == request.user.employer_profile.id
        
        return False


class IsEmployeeOrEmployerOrAdmin(permissions.BasePermission):
    """
    Permission to allow employees to access their own trips,
    employers to access their employees' trips, and admins to access all trips.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.is_employee or request.user.is_employer or 
             request.user.is_super_admin or request.user.is_bank_admin)
        )
    
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any trip
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Employee can access their own trips
        if hasattr(obj, 'employee') and hasattr(request.user, 'employee_profile'):
            return obj.employee == request.user.employee_profile
            
        # Employer can access their employees' trips
        if hasattr(obj, 'employee') and hasattr(request.user, 'employer_profile'):
            return obj.employee.employer == request.user.employer_profile
            
        return False


class IsCreditOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of the carbon credits or admins to access them.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any credits
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # If the owner is an employee
        if obj.owner_type == 'employee' and hasattr(request.user, 'employee_profile'):
            return obj.owner_id == request.user.employee_profile.id
            
        # If the owner is an employer
        if obj.owner_type == 'employer' and hasattr(request.user, 'employer_profile'):
            return obj.owner_id == request.user.employer_profile.id
            
        # If the user is an employer and the credit belongs to their employee
        if obj.owner_type == 'employee' and hasattr(request.user, 'employer_profile'):
            try:
                employee = EmployeeProfile.objects.get(id=obj.owner_id)
                return employee.employer == request.user.employer_profile
            except EmployeeProfile.DoesNotExist:
                return False
                
        return False 