"""
Enhanced NLP Service for Advanced Sustainability Insights
Handles natural language queries, carbon footprint analysis, and personalized recommendations
"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from django.conf import settings
from users.models import CustomUser
from .pollution_models import IndustrialZone
from trips.models import Trip, CarbonCredit
from .pollution_service import PollutionDataService
import openai

class EnhancedNLPService:
    """Advanced NLP service for carbon footprint queries and insights"""
    
    def __init__(self):
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.pollution_service = PollutionDataService()
        
    def process_user_query(self, user_id: int, query: str) -> Dict[str, Any]:
        """
        Process natural language queries about carbon footprint and sustainability
        Examples:
        - "How much CO₂ did I save this week?"
        - "What's my carbon footprint this month?"
        - "Compare my savings to planting trees"
        - "How many factory hours did I offset?"
        """
        
        try:
            # Extract user data
            user_data = self._get_user_carbon_data(user_id)
            
            # Analyze query intent
            intent = self._analyze_query_intent(query)
            
            # Generate response based on intent
            response = self._generate_response(intent, user_data, query)
            
            return {
                'success': True,
                'response': response,
                'intent': intent,
                'data': user_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': 'I apologize, but I had trouble processing your query. Please try again.'
            }
    
    def _get_user_carbon_data(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive carbon data for user"""
        try:
            user = CustomUser.objects.get(id=user_id)
            employee_profile = getattr(user, 'employee_profile', None)
            if not employee_profile:
                return {
                    'total_credits': 0,
                    'weekly_trips': 0,
                    'monthly_trips': 0,
                    'weekly_savings': 0,
                    'monthly_savings': 0,
                    'recent_trips': []
                }
            
            # Get trips from last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_trips = Trip.objects.filter(
                employee=employee_profile,
                start_time__gte=thirty_days_ago
            )
            
            # Get trips from last 7 days
            seven_days_ago = datetime.now() - timedelta(days=7)
            weekly_trips = Trip.objects.filter(
                employee=employee_profile,
                start_time__gte=seven_days_ago
            )
            
            # Calculate totals
            total_credits = CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id=employee_profile.id,
                status='active'
            ).count()
            weekly_savings = sum(
                float(trip.carbon_savings or trip.carbon_credits_earned or trip.credits_earned or 0)
                for trip in weekly_trips
            )
            monthly_savings = sum(
                float(trip.carbon_savings or trip.carbon_credits_earned or trip.credits_earned or 0)
                for trip in recent_trips
            )
            
            return {
                'total_credits': total_credits,
                'weekly_trips': weekly_trips.count(),
                'monthly_trips': recent_trips.count(),
                'weekly_savings': weekly_savings,
                'monthly_savings': monthly_savings,
                'recent_trips': [
                    {
                        'date': trip.start_time.strftime('%Y-%m-%d'),
                        'mode': trip.transport_mode,
                        'savings': float(trip.carbon_savings or trip.carbon_credits_earned or trip.credits_earned or 0)
                    } for trip in recent_trips[:5]
                ]  # Last 5 trips
            }
            
        except Exception as e:
            raise Exception(f"Error getting user carbon data: {str(e)}")
    
    def _analyze_query_intent(self, query: str) -> str:
        """Analyze user query to determine intent"""
        query_lower = query.lower()
        
        # Define intent patterns
        intents = {
            'weekly_savings': [
                'week', 'this week', 'past week', 'last 7 days', 'weekly'
            ],
            'monthly_savings': [
                'month', 'this month', 'past month', 'last 30 days', 'monthly'
            ],
            'total_savings': [
                'total', 'overall', 'all time', 'ever', 'total savings'
            ],
            'tree_equivalent': [
                'tree', 'trees', 'planting', 'forest', 'equivalent'
            ],
            'factory_hours': [
                'factory', 'industrial', 'hours', 'offset', 'factory hours'
            ],
            'comparison': [
                'compare', 'versus', 'vs', 'compared to', 'better than'
            ],
            'prediction': [
                'predict', 'forecast', 'future', 'next', 'upcoming'
            ],
            'tips': [
                'tips', 'advice', 'recommend', 'suggest', 'how to'
            ]
        }
        
        # Check for each intent
        for intent, keywords in intents.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        return 'general'
    
    def _generate_response(self, intent: str, user_data: Dict[str, Any], original_query: str) -> str:
        """Generate contextual response based on intent and user data"""
        
        if intent == 'weekly_savings':
            return self._generate_weekly_savings_response(user_data)
        elif intent == 'monthly_savings':
            return self._generate_monthly_savings_response(user_data)
        elif intent == 'total_savings':
            return self._generate_total_savings_response(user_data)
        elif intent == 'tree_equivalent':
            return self._generate_tree_equivalent_response(user_data)
        elif intent == 'factory_hours':
            return self._generate_factory_hours_response(user_data)
        elif intent == 'comparison':
            return self._generate_comparison_response(user_data, original_query)
        elif intent == 'prediction':
            return self._generate_prediction_response(user_data)
        elif intent == 'tips':
            return self._generate_tips_response(user_data)
        else:
            return self._generate_general_response(user_data, original_query)
    
    def _generate_weekly_savings_response(self, user_data: Dict[str, Any]) -> str:
        """Generate response for weekly savings query"""
        weekly_savings = user_data['weekly_savings']
        weekly_trips = user_data['weekly_trips']
        
        if weekly_savings > 0:
            trees_equivalent = weekly_savings / 21  # 1 tree absorbs 21kg CO2/year
            factory_hours = weekly_savings / 2.5  # Average factory emits 2.5kg CO2/hour
            
            return f"""🌟 **Your Weekly Impact!**

This week you've saved **{weekly_savings:.1f} kg CO₂** through **{weekly_trips} eco-friendly trips**!

🌱 **Environmental Impact:**
• Equivalent to planting **{trees_equivalent:.1f} trees** 🌳
• Offsets **{factory_hours:.1f} hours** of factory emissions 🏭
• You're making a real difference! 💚

Keep up the great work! Every eco-friendly choice adds up to significant positive impact."""
        
        else:
            return """🌱 **Start Your Eco-Journey!**

I don't see any carbon savings from this week yet. Every eco-friendly trip counts!

💡 **Quick Tips:**
• Try walking or cycling for short distances
• Use public transport when possible
• Carpool with colleagues
• Consider remote work options

Ready to make a positive impact? Start with your next eco-friendly trip! 🚴‍♀️"""
    
    def _generate_monthly_savings_response(self, user_data: Dict[str, Any]) -> str:
        """Generate response for monthly savings query"""
        monthly_savings = user_data['monthly_savings']
        monthly_trips = user_data['monthly_trips']
        
        if monthly_savings > 0:
            trees_equivalent = monthly_savings / 21
            factory_hours = monthly_savings / 2.5
            
            return f"""📊 **Your Monthly Achievement!**

This month you've saved **{monthly_savings:.1f} kg CO₂** through **{monthly_trips} sustainable trips**!

🌍 **Monthly Impact:**
• Equivalent to planting **{trees_equivalent:.1f} trees** 🌳
• Offsets **{factory_hours:.1f} hours** of factory emissions 🏭
• That's amazing consistency! 🏆

Your commitment to sustainability is inspiring. Keep leading by example! 💚"""
        
        else:
            return """📅 **Monthly Fresh Start!**

This month is your opportunity to make a difference!

🎯 **Monthly Goals:**
• Aim for 10+ eco-friendly trips
• Target 50kg+ CO₂ savings
• Try 3 different transport modes

Every sustainable choice contributes to a greener future. Start today! 🌱"""
    
    def _generate_tree_equivalent_response(self, user_data: Dict[str, Any]) -> str:
        """Generate response with tree planting equivalents"""
        total_savings = user_data['monthly_savings']  # Use monthly as default
        trees_equivalent = total_savings / 21
        
        return f"""🌳 **Your Tree Planting Impact!**

Your carbon savings of **{total_savings:.1f} kg CO₂** is equivalent to:

🌱 **{trees_equivalent:.1f} mature trees** planted and grown for one year!
📏 That's about **{trees_equivalent * 2:.0f} meters** of forest coverage
🏭 Or **{total_savings / 2.5:.1f} hours** of offset factory emissions

🌍 **Environmental Impact:**
• Each tree absorbs ~21kg CO₂ annually
• Trees provide oxygen, habitat, and prevent erosion
• Your contribution helps combat climate change

You're literally growing a greener future! 🌲💚"""
    
    def _generate_factory_hours_response(self, user_data: Dict[str, Any]) -> str:
        """Generate response with factory hour equivalents"""
        total_savings = user_data['monthly_savings']
        factory_hours = total_savings / 2.5
        
        return f"""🏭 **Industrial Impact Offset!**

Your carbon savings of **{total_savings:.1f} kg CO₂** has offset:

⏱️ **{factory_hours:.1f} hours** of typical industrial factory emissions!
🏭 That's equivalent to shutting down a factory for **{factory_hours/24:.1f} days**
⚡ Prevented significant air and water pollution

🌍 **Context:**
• Average factory emits 2.5kg CO₂ per hour
• Your choices directly reduce industrial pollution
• Every kg saved matters for air quality

You're a pollution-fighting hero! 🦸‍♀️💚"""
    
    def _generate_comparison_response(self, user_data: Dict[str, Any], query: str) -> str:
        """Generate comparison-based response"""
        # Extract comparison target from query
        if 'car' in query.lower():
            return self._compare_to_car(user_data)
        elif 'bus' in query.lower():
            return self._compare_to_bus(user_data)
        else:
            return self._generate_general_response(user_data, query)
    
    def _compare_to_car(self, user_data: Dict[str, Any]) -> str:
        """Compare user's savings to car emissions"""
        user_savings = user_data['monthly_savings']
        car_equivalent = user_savings * 2.5  # Cars emit ~2.5x more than eco transport
        
        return f"""🚗 **vs Car Comparison!**

Your eco-friendly choices have saved **{user_savings:.1f} kg CO₂**!

📊 **If you drove instead:**
• Car trips would emit **{car_equivalent:.1f} kg CO₂**
• You saved **{car_equivalent - user_savings:.1f} kg** extra emissions
• That's **{((car_equivalent/user_savings) - 1) * 100:.0f}%** more pollution!

🌱 **Your Impact:**
• Prevented equivalent of **{car_equivalent/10:.0f} liters** of fuel consumption
• Reduced traffic congestion and air pollution
• Contributed to cleaner city air

Smart choice for the planet! 🌍💚"""
    
    def _generate_prediction_response(self, user_data: Dict[str, Any]) -> str:
        """Generate predictive insights"""
        current_savings = user_data['monthly_savings']
        weekly_average = current_savings / 4  # Approximate weekly average
        
        # Simple prediction based on current trend
        predicted_monthly = current_savings * 1.2  # 20% improvement prediction
        predicted_trees = predicted_monthly / 21
        
        return f"""🔮 **Your Sustainability Forecast!**

Based on your current eco-friendly patterns:

📈 **Next Month Prediction:**
• Expected savings: **{predicted_monthly:.1f} kg CO₂**
• Tree equivalent: **{predicted_trees:.1f} trees** 🌳
• Improvement potential: **20% growth** 📊

🎯 **To Exceed Predictions:**
• Add 1-2 more eco-trips per week
• Try a new sustainable transport mode
• Encourage friends to join you

🌟 You're on track to become a sustainability champion! Keep it up! 💚"""
    
    def _generate_tips_response(self, user_data: Dict[str, Any]) -> str:
        """Generate personalized eco-tips"""
        weekly_trips = user_data['weekly_trips']
        
        tips = []
        
        if weekly_trips < 5:
            tips.append("🚴‍♀️ **Increase trip frequency**: Aim for 5+ eco-friendly trips weekly")
        
        if weekly_trips > 0:
            tips.append("🌱 **Mix transport modes**: Try cycling, walking, or public transport")
        
        tips.append("👥 **Carpool smart**: Share rides to multiply impact")
        tips.append("⏰ **Off-peak travel**: Avoid rush hour for better air quality")
        tips.append("📱 **Trip chaining**: Combine multiple errands in one trip")
        
        return f"""💡 **Personalized Eco-Tips for You!**

Based on your activity level (**{weekly_trips} trips this week**):

{chr(10).join(tips)}

🌟 **Bonus Tip:**
Track your progress to see how small changes create big impacts! Every sustainable choice matters.

Ready to level up your eco-game? 🌍💚"""
    
    def _generate_general_response(self, user_data: Dict[str, Any], query: str) -> str:
        """Generate response using AI for general queries"""
        try:
            # Use OpenRouter for general queries
            context = f"""
            User Carbon Data:
            - Total Credits: {user_data['total_credits']}
            - Weekly Trips: {user_data['weekly_trips']}
            - Monthly Savings: {user_data['monthly_savings']:.1f} kg CO₂
            
            User Query: {query}
            
            Please provide a helpful, encouraging response about their carbon footprint and sustainability journey.
            Focus on positive reinforcement and actionable advice.
            """
            
            response = self._call_openrouter_api(context)
            return response
            
        except Exception as e:
            return f"""🌱 **I'm here to help!**

I can help you understand your carbon footprint and sustainability journey. Try asking about:

📊 **Your Impact:**
• "How much CO₂ did I save this week?"
• "What's my monthly carbon footprint?"
• "Compare my savings to planting trees"

🎯 **Predictions:**
• "Predict my next month's impact"
• "How can I improve my eco-score?"

💡 **Tips & Advice:**
• "Give me eco-friendly tips"
• "How can I save more CO₂?"

I'm learning more about sustainability every day. What would you like to know? 🌍💚"""
    
    def _call_openrouter_api(self, prompt: str) -> str:
        """Call OpenRouter API for AI responses"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "anthropic/claude-3-haiku",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API Error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"OpenRouter API call failed: {str(e)}")
    
    def get_carbon_insights(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive carbon insights for dashboard"""
        try:
            user_data = self._get_user_carbon_data(user_id)
            
            # Calculate additional metrics
            monthly_savings = user_data['monthly_savings']
            trees_equivalent = monthly_savings / 21
            factory_hours = monthly_savings / 2.5
            
            # Get trend data
            insights = {
                'current_month': {
                    'savings_kg': monthly_savings,
                    'trees_equivalent': trees_equivalent,
                    'factory_hours': factory_hours,
                    'trips_count': user_data['monthly_trips'],
                    'credits_earned': user_data['total_credits']
                },
                'weekly_average': {
                    'savings_kg': monthly_savings / 4,
                    'trips_count': user_data['weekly_trips']
                },
                'environmental_impact': {
                    'trees_planted': trees_equivalent,
                    'factory_hours_offset': factory_hours,
                    'cars_off_road': monthly_savings / 2.5,
                    'fuel_saved_liters': monthly_savings * 0.5  # Approximate
                },
                'recent_activity': [
                    {
                        'date': trip.created_at.strftime('%Y-%m-%d'),
                        'mode': trip.transport_mode,
                        'savings': trip.carbon_saved
                    } for trip in user_data['recent_trips']
                ]
            }
            
            return insights
            
        except Exception as e:
            raise Exception(f"Error generating carbon insights: {str(e)}")
