from rest_framework import permissions
from users.models import EmployerProfile

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
        
        # For market offers, check if the user is the seller
        if hasattr(obj, 'seller') and hasattr(request.user, 'employer_profile'):
            return obj.seller == request.user.employer_profile
            
        return False
        
        
class IsOfferParticipantOrAdmin(permissions.BasePermission):
    """
    Permission to allow only participants of a transaction or admins to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any object
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Check if the user is the buyer or seller
        if hasattr(request.user, 'employer_profile'):
            if hasattr(obj, 'buyer') and obj.buyer == request.user.employer_profile:
                return True
                
            if hasattr(obj, 'seller') and obj.seller == request.user.employer_profile:
                return True
                
        return False
        

class IsOfferSellerOrAdmin(permissions.BasePermission):
    """
    Permission to allow only the seller of an offer or admins to modify it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins and bank admins to access any object
        if request.user.is_super_admin or request.user.is_bank_admin:
            return True
        
        # Check if the user is the seller
        if hasattr(request.user, 'employer_profile') and hasattr(obj, 'seller'):
            return obj.seller == request.user.employer_profile
            
        return False 