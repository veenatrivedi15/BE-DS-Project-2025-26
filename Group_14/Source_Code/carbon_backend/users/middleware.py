from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from re import compile

class ApprovalMiddleware:
    """
    Middleware to check if a user is approved and redirect to the pending approval page if not.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile the public URL patterns that don't require approval
        self.public_urls = compile(r'^/(?:login|logout|register|registration/pending-approval|api|admin|static|media).*$')
        
    def __call__(self, request):
        # Skip check for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Skip check for super admins and bank admins
        if request.user.is_super_admin or request.user.is_bank_admin:
            return self.get_response(request)
            
        # Skip check for public URLs
        if self.public_urls.match(request.path):
            return self.get_response(request)
            
        # Check if user is approved
        if not request.user.approved:
            # Set registration type based on user role
            if request.user.is_employee:
                request.session['registration_type'] = 'employee'
            elif request.user.is_employer:
                request.session['registration_type'] = 'employer'
                
            # Add message if not already on pending approval page
            if request.path != reverse('pending_approval'):
                messages.info(request, "Your account is pending approval. You'll be notified once it's approved.")
                
            # Redirect to pending approval page
            return redirect('pending_approval')
            
        # User is approved, continue with the request
        return self.get_response(request) 