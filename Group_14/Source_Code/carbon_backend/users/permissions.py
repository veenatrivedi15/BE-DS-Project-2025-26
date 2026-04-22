from rest_framework import permissions


class IsEmployer(permissions.BasePermission):
    """
    Permission to only allow employers to access the view.
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
        
        # For employer profiles, check if the user is the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For employees, check if they belong to the employer
        if hasattr(obj, 'employer') and hasattr(request.user, 'employer_profile'):
            return obj.employer == request.user.employer_profile
        
        return False


class IsEmployee(permissions.BasePermission):
    """
    Permission to only allow employees to access the view.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.is_employee or request.user.is_super_admin or 
             request.user.is_bank_admin or request.user.is_employer)
        )
    
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any object
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # For employee profiles, check if the user is the owner or their employer
        if hasattr(obj, 'user'):
            if obj.user == request.user:
                return True
            
            # Check if the user is the employer of this employee
            if (hasattr(request.user, 'employer_profile') and 
                hasattr(obj, 'employer') and 
                obj.employer == request.user.employer_profile):
                return True
        
        return False


class IsBankAdmin(permissions.BasePermission):
    """
    Permission to only allow bank admins to access the view.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.is_bank_admin or request.user.is_super_admin)
        )


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission to only allow super admins to access the view.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_super_admin)


class IsEmployerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow access to employers or admins.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and is an employer, bank admin, or super admin
        if not (request.user and request.user.is_authenticated):
            return False
        
        return (request.user.is_employer or 
                request.user.is_bank_admin or 
                request.user.is_super_admin)


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and is either a bank admin or super admin
        if not (request.user and request.user.is_authenticated):
            return False
        
        return request.user.is_bank_admin or request.user.is_super_admin


class IsSameEmployerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow employers to access their own employees
    or admins to access any.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins can access any employee
        if request.user.is_bank_admin or request.user.is_super_admin:
            return True
            
        # Employers can only access their own employees
        if request.user.is_employer and hasattr(request.user, 'employer_profile'):
            return obj.employer == request.user.employer_profile
            
        return False 


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of an object or admins to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any object
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Check if the user is the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If it's a location, check if created by the user or belongs to their employer
        if hasattr(obj, 'created_by'):
            if obj.created_by == request.user:
                return True
            
            # Employers can access locations for their company
            if (hasattr(request.user, 'employer_profile') and 
                hasattr(obj, 'employer') and 
                obj.employer == request.user.employer_profile):
                return True
            
            # Employees can access their employer's locations
            if (hasattr(request.user, 'employee_profile') and 
                hasattr(obj, 'employer') and 
                obj.employer == request.user.employee_profile.employer):
                return True
        
        return False


class IsApprovedUser(permissions.BasePermission):
    """
    Permission to only allow approved users to access the view.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Super admins and bank admins are always approved
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Check approval status
        return request.user.is_approved_role() 