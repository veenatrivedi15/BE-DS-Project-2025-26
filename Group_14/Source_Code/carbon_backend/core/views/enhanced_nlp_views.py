"""
Enhanced NLP Views for Advanced Sustainability Insights
Handles natural language queries, carbon footprint analysis, and personalized recommendations
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..enhanced_nlp_service import EnhancedNLPService
from users.models import CustomUser

# Initialize the enhanced NLP service
nlp_service = EnhancedNLPService()

@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required
def process_nlp_query(request):
    """
    Process natural language queries about carbon footprint and sustainability
    """
    if request.method == 'GET':
        query = request.GET.get('query', '')
    else:
        data = json.loads(request.body)
        query = data.get('query', '')
    
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Query is required'
        }, status=400)
    
    try:
        user_id = request.user.id
        result = nlp_service.process_user_query(user_id, query)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def chat_api(request):
    """
    Chat API for real-time AI conversations
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        user_id = request.user.id
        result = nlp_service.process_user_query(user_id, message)
        
        return JsonResponse({
            'success': True,
            'response': result.get('response', 'I apologize, but I couldn\'t process your request.'),
            'timestamp': result.get('timestamp', '')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def nlp_dashboard(request):
    """
    Enhanced NLP Dashboard view
    """
    return render(request, 'enhanced_nlp/dashboard.html')

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def get_carbon_insights(request):
    """
    Get comprehensive carbon insights for dashboard
    """
    try:
        user_id = request.user.id
        insights = nlp_service.get_carbon_insights(user_id)
        
        return JsonResponse({
            'success': True,
            'insights': insights
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def get_sustainability_tips(request):
    """
    Get personalized sustainability tips
    """
    try:
        user_id = request.user.id
        user_data = nlp_service._get_user_carbon_data(user_id)
        
        # Generate contextual tips based on user activity
        tips = []
        weekly_trips = user_data['weekly_trips']
        monthly_savings = user_data['monthly_savings']
        
        if weekly_trips < 3:
            tips.append({
                'type': 'activity',
                'title': 'Increase Your Eco-Trips',
                'description': 'Try to make 3-5 eco-friendly trips per week for maximum impact',
                'priority': 'high',
                'icon': '🚴‍♀️'
            })
        
        if monthly_savings < 20:
            tips.append({
                'type': 'savings',
                'title': 'Boost Your Carbon Savings',
                'description': 'Aim for 20kg+ CO₂ savings monthly to plant one tree equivalent',
                'priority': 'medium',
                'icon': '🌱'
            })
        
        # Add general tips
        tips.extend([
            {
                'type': 'transport',
                'title': 'Mix Your Transport Modes',
                'description': 'Combine walking, cycling, and public transport for variety',
                'priority': 'medium',
                'icon': '🚌'
            },
            {
                'type': 'social',
                'title': 'Share Your Impact',
                'description': 'Encourage friends to join your eco-journey',
                'priority': 'low',
                'icon': '👥'
            }
        ])
        
        return JsonResponse({
            'success': True,
            'tips': tips,
            'user_stats': {
                'weekly_trips': weekly_trips,
                'monthly_savings': monthly_savings
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def get_environmental_impact(request):
    """
    Get detailed environmental impact calculations
    """
    try:
        user_id = request.user.id
        insights = nlp_service.get_carbon_insights(user_id)
        impact = insights['environmental_impact']
        
        # Add more detailed calculations
        impact['co2_absorption_days'] = impact['trees_planted'] * 365  # Days of CO2 absorption
        impact['air_quality_improvement'] = impact['cars_off_road'] * 0.8  # Air quality index improvement
        impact['energy_saved'] = impact['fuel_saved_liters'] * 9.7  # kWh energy equivalent
        
        return JsonResponse({
            'success': True,
            'impact': impact,
            'summary': {
                'trees_equivalent': f"{impact['trees_planted']:.1f} trees",
                'factory_hours': f"{impact['factory_hours_offset']:.1f} hours",
                'cars_off_road': f"{impact['cars_off_road']:.1f} cars",
                'energy_saved': f"{impact['energy_saved']:.1f} kWh"
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
