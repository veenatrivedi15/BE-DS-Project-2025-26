from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from .views.profile_router import profile_router

urlpatterns = [
    path('', login_required(profile_router), name='profile_router'),
] 