from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, EmployerProfile, EmployeeProfile, Location


class CustomUserAdmin(UserAdmin):
    """Admin configuration for the CustomUser model."""
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Role info'), {
            'fields': ('is_employee', 'is_employer', 'is_bank_admin', 'is_super_admin', 'approved'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    list_display = ['email', 'username', 'first_name', 'last_name', 'get_role_display',
                    'is_staff', 'approved', 'is_active']
    list_filter = ['is_employee', 'is_employer', 'is_bank_admin', 'is_super_admin', 
                   'is_staff', 'approved', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    actions = ['approve_users', 'reject_users']
    
    def get_role_display(self, obj):
        return obj.get_role().replace('_', ' ').title()
    get_role_display.short_description = 'Role'
    
    def approve_users(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} users have been approved.")
    approve_users.short_description = "Approve selected users"
    
    def reject_users(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} users have been rejected.")
    reject_users.short_description = "Reject selected users"


class EmployerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for the EmployerProfile model."""
    
    list_display = ['company_name', 'user', 'registration_number', 'industry', 'approved', 'created_at']
    list_filter = ['approved', 'industry']
    search_fields = ['company_name', 'registration_number', 'user__email']
    readonly_fields = ['created_at']
    actions = ['approve_employers', 'reject_employers']
    
    def approve_employers(self, request, queryset):
        # Update both the profile and the user
        for profile in queryset:
            profile.approved = True
            profile.save()
            profile.user.approved = True
            profile.user.save()
        
        self.message_user(request, f"{queryset.count()} employers have been approved.")
    approve_employers.short_description = "Approve selected employers"
    
    def reject_employers(self, request, queryset):
        # Update both the profile and the user
        for profile in queryset:
            profile.approved = False
            profile.save()
            profile.user.approved = False
            profile.user.save()
        
        self.message_user(request, f"{queryset.count()} employers have been rejected.")
    reject_employers.short_description = "Reject selected employers"


class EmployeeProfileAdmin(admin.ModelAdmin):
    """Admin configuration for the EmployeeProfile model."""
    
    list_display = ['user', 'employer', 'approved', 'created_at']
    list_filter = ['approved', 'employer']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'employer__company_name']
    readonly_fields = ['created_at']
    actions = ['approve_employees', 'reject_employees']
    
    def approve_employees(self, request, queryset):
        # Update both the profile and the user
        for profile in queryset:
            profile.approved = True
            profile.save()
            profile.user.approved = True
            profile.user.save()
        
        self.message_user(request, f"{queryset.count()} employees have been approved.")
    approve_employees.short_description = "Approve selected employees"
    
    def reject_employees(self, request, queryset):
        # Update both the profile and the user
        for profile in queryset:
            profile.approved = False
            profile.save()
            profile.user.approved = False
            profile.user.save()
        
        self.message_user(request, f"{queryset.count()} employees have been rejected.")
    reject_employees.short_description = "Reject selected employees"


class LocationAdmin(admin.ModelAdmin):
    """Admin configuration for the Location model."""
    
    list_display = ['address', 'location_type', 'created_by', 'employer', 'is_primary', 'created_at']
    list_filter = ['location_type', 'is_primary']
    search_fields = ['address', 'created_by__email', 'employer__company_name']
    readonly_fields = ['created_at']


# Register models with admin
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EmployerProfile, EmployerProfileAdmin)
admin.site.register(EmployeeProfile, EmployeeProfileAdmin)
admin.site.register(Location, LocationAdmin)
