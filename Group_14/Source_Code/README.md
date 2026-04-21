# Carbon Credits Platform

A comprehensive platform for tracking, managing, and trading carbon credits generated from eco-friendly commuting.

## Project Structure

This project is built with Django, using Django Templates with HTMX for interactive functionality and Tailwind CSS for styling:

- **Django Backend & Frontend**: 
  - Complete user management with role-based access
  - Trip tracking and verification
  - Carbon credit generation and marketplace
  - Dynamic interfaces with HTMX
  - Responsive design with Tailwind CSS

## Current Status

The application is fully functional with:
- User registration and authentication
- Role-based dashboards for different user types
- Trip logging and carbon credit calculation
- Credit trading marketplace
- Admin management tools

## Getting Started

### Project Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createuser --role=super_admin --email=admin@example.com --password=Admin123! --first_name=Admin --last_name=User --approved

# Install Tailwind CSS dependencies
python manage.py tailwind install

# Run Tailwind CSS in development mode
python manage.py tailwind start

# Start development server (in another terminal)
python manage.py runserver
```

## Technology Stack

- **Backend & Templates**:
  - Django 5.2
  - Django Templates
  - HTMX for dynamic interactions
  - SQLite (for development)
  - PostgreSQL (for production)

- **Frontend**:
  - Tailwind CSS
  - HTMX
  - Alpine.js (for complex client-side interactions)
  - Chart.js (for data visualization)

## Key Features

- **User Management**:
  - Role-based access control (Super Admin, Bank Admin, Employer, Employee)
  - Registration and approval workflows
  - Profile management

- **Trip Tracking**:
  - Start/end trip tracking with geolocation
  - Transport mode selection
  - Distance and carbon savings calculation
  - Trip verification

- **Carbon Credits**:
  - Automatic credit generation based on trips
  - Credit history and statistics
  - Credit redemption

- **Marketplace**:
  - Credit trading between organizations
  - Offer creation and management
  - Transaction history
  - Admin approval for large transactions

## License

This project is licensed under the MIT License - see the LICENSE file for details. 