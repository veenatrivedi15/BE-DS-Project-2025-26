"""
Django management command to train the carbon credits ML model.

Usage:
    python manage.py train_carbon_model
"""

from django.core.management.base import BaseCommand
import sys
import os

# Add ml_training to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml_training'))

from train_model import train_model


class Command(BaseCommand):
    help = 'Train the carbon credits prediction ML model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ML model training...'))
        self.stdout.write('=' * 60)
        
        try:
            train_model()
            self.stdout.write(self.style.SUCCESS('\n✅ Model training completed successfully!'))
            self.stdout.write('Model files saved to: ml_models/')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error training model: {str(e)}'))
            raise


