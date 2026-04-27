"""
Views for displaying inspirational quotes about saving the environment.
Shown after login to motivate users.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import random

# Collection of environmental quotes
ENVIRONMENTAL_QUOTES = [
    {
        'quote': "The Earth does not belong to us; we belong to the Earth. All things are connected like the blood that unites one family.",
        'author': "Chief Seattle"
    },
    {
        'quote': "The greatest threat to our planet is the belief that someone else will save it.",
        'author': "Robert Swan"
    },
    {
        'quote': "We do not inherit the Earth from our ancestors; we borrow it from our children.",
        'author': "Native American Proverb"
    },
    {
        'quote': "The environment is where we all meet; where we all have a mutual interest; it is the one thing all of us share.",
        'author': "Lady Bird Johnson"
    },
    {
        'quote': "What we are doing to the forests of the world is but a mirror reflection of what we are doing to ourselves and to one another.",
        'author': "Mahatma Gandhi"
    },
    {
        'quote': "The Earth is what we all have in common.",
        'author': "Wendell Berry"
    },
    {
        'quote': "Climate change is no longer some far-off problem; it is happening here, it is happening now.",
        'author': "Barack Obama"
    },
    {
        'quote': "Every small action counts. Together, we can make a big difference for our planet.",
        'author': "Unknown"
    },
    {
        'quote': "The best time to plant a tree was 20 years ago. The second best time is now.",
        'author': "Chinese Proverb"
    },
    {
        'quote': "Sustainability is no longer about doing less harm. It's about doing more good.",
        'author': "Jochen Zeitz"
    },
    {
        'quote': "We are the first generation to feel the impact of climate change and the last generation that can do something about it.",
        'author': "Barack Obama"
    },
    {
        'quote': "The future will either be green or not at all.",
        'author': "Bob Brown"
    },
    {
        'quote': "One person's actions may seem small, but when multiplied by millions, they can change the world.",
        'author': "Unknown"
    },
    {
        'quote': "The environment and the economy are really both two sides of the same coin. If we cannot sustain the environment, we cannot sustain ourselves.",
        'author': "Wangari Maathai"
    },
    {
        'quote': "Every journey of a thousand miles begins with a single step. Start your sustainable journey today.",
        'author': "Lao Tzu (adapted)"
    }
]

@login_required
def quote_page(request):
    """
    Display an inspirational environmental quote after login.
    Users can skip or continue to their dashboard.
    """
    # Check if user has already seen a quote today (optional - can be removed if you want to show every time)
    # For now, we'll show a random quote each time
    
    # Get a random quote
    quote_data = random.choice(ENVIRONMENTAL_QUOTES)
    
    # Determine redirect URL based on user type
    if request.user.is_employee:
        redirect_url = 'employee_dashboard'
    elif request.user.is_employer:
        redirect_url = 'employer:employer_dashboard'
    elif request.user.is_super_admin or request.user.is_bank_admin:
        redirect_url = 'admin_dashboard'
    else:
        redirect_url = 'employee_dashboard'  # Default fallback
    
    context = {
        'quote': quote_data['quote'],
        'author': quote_data['author'],
        'redirect_url': redirect_url,
        'page_title': 'Inspiration for a Sustainable Future'
    }
    
    return render(request, 'quote.html', context)

