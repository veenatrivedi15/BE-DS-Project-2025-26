from django.urls import path
from core.views.employer_views import (
    dashboard, employees_list, locations_list, trading,
    pending_trips, trip_approval, create_transaction, create_offer,
    mark_notification_read, employee_approval, invite_employee,
    location_add, location_edit, location_delete, location_set_primary,
    profile, update_profile, change_password, employee_marketplace
)
from core.views.employer_redemption_views import redemption_requests, process_redemption

app_name = 'employer'

urlpatterns = [
    path('dashboard/', dashboard, name='employer_dashboard'),
    path('employees/', employees_list, name='employees'),
    path('employees/<int:employee_id>/approval/', employee_approval, name='employee_approval'),
    path('employees/invite/', invite_employee, name='invite_employee'),
    path('locations/', locations_list, name='locations'),
    path('locations/add/', location_add, name='location_add'),
    path('locations/<int:location_id>/edit/', location_edit, name='location_edit'),
    path('locations/<int:location_id>/delete/', location_delete, name='location_delete'),
    path('locations/<int:location_id>/set-primary/', location_set_primary, name='location_set_primary'),
    path('trading/', trading, name='trading'),
    path('trading/create-transaction/', create_transaction, name='create_transaction'),
    path('trading/create-offer/', create_offer, name='create_offer'),
    path('trips/pending/', pending_trips, name='pending_trips'),
    path('trips/<int:trip_id>/approve/', trip_approval, name='trip_approval'),
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('employee-marketplace/', employee_marketplace, name='employee_marketplace'),
    path('redemption-requests/', redemption_requests, name='redemption_requests'),
    path('redemption-requests/<int:request_id>/process/', process_redemption, name='process_redemption'),
    
    # Profile
    path('profile/', profile, name='profile'),
    path('profile/update/', update_profile, name='update_profile'),
    path('profile/change-password/', change_password, name='change_password'),
] 