"""
URL configuration for carbon_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.generic import TemplateView
from django.shortcuts import redirect, HttpResponseRedirect
from users.models import EmployerProfile
from core.views.api_views import get_environment_data
from core.views.quote_views import quote_page
from core.views.auth_views import login_view

# API URLs
api_urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', include('users.urls')),
    path('trips/', include('trips.urls')),
    path('marketplace/', include('marketplace.urls')),
]

# Landing page view
class LandingPageView(TemplateView):
    template_name = 'landing.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

# Registration view with employers list
class RegisterView(TemplateView):
    template_name = 'auth/register.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all approved employers
        context['employers'] = EmployerProfile.objects.filter(approved=True)
        return context

# Dashboard redirect function
def dashboard_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_super_admin:
        return redirect('admin_dashboard')
    elif request.user.is_bank_admin:
        return redirect('bank:bank_dashboard')
    elif request.user.is_employer:
        return redirect('employer:employer_dashboard')
    elif request.user.is_employee:
        return redirect('employee_dashboard')
    else:
        # Fallback to employee dashboard if no specific role is set
        return redirect('employee_dashboard')

# Profile redirect function
def profile_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_super_admin:
        return redirect('admin_profile')
    elif request.user.is_bank_admin:
        return redirect('bank:profile')
    elif request.user.is_employer:
        return redirect('employer:profile')
    elif request.user.is_employee:
        return redirect('employee_profile')
    else:
        # Fallback to login if no specific role is set
        return redirect('login')

# Custom logout view function
def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

# Template-based URLs
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # API routes
    path('api/', include(api_urlpatterns)),
    path('api/environment-data/', get_environment_data, name='api_environment_data'),
    
    # Notification routes
    path('api/notifications/', include('core.notification_urls')),
    
    # Auth routes
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', profile_redirect, name='profile'),
    path('quote/', quote_page, name='quote_page'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
    path('registration/pending-approval/', TemplateView.as_view(template_name='registration/pending_approval.html'), name='pending_approval'),
    
    # Main routes
    path('', LandingPageView.as_view(), name='home'),
    path('dashboard/', dashboard_redirect, name='dashboard'),
    
    # Include app-specific template URLs
    path('systemadmin/', include('core.admin_urls')),  # Custom admin views
    path('bank/', include('core.bank_urls')),
    path('employer/', include('core.employer_urls')),
    path('employee/', include('core.employee_urls')),
    path('', include('core.urls')),  # Core functionality URLs
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
