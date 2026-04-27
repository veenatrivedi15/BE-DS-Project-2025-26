from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from users.models import CustomUser, EmployerProfile
from trips.models import CarbonCredit


class Command(BaseCommand):
    help = "Create test carbon credits for an employer account"

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=False, help='Email of the employer user')
        parser.add_argument('--amount', type=float, default=100.0, help='Amount of credits to add')

    def handle(self, *args, **options):
        email = options.get('email')
        credit_amount = Decimal(str(options.get('amount')))

        if not email:
            email = 'acme@example.com'

        try:
            with transaction.atomic():
                # Find the user by email
                try:
                    user = CustomUser.objects.get(email=email)
                except CustomUser.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"No user found with email {email}"))
                    return

                # Check if user is an employer
                if not user.is_employer:
                    self.stdout.write(self.style.ERROR(f"User {email} is not an employer"))
                    return

                # Get employer profile
                try:
                    employer = user.employer_profile
                except EmployerProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"No employer profile found for {email}"))
                    return

                # Create carbon credits
                credit = CarbonCredit.objects.create(
                    amount=credit_amount,
                    source_trip=None,
                    owner_type='employer',
                    owner_id=employer.id,
                    timestamp=timezone.now(),
                    status='active',
                    expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                )

                # Calculate total credits
                total_credits = CarbonCredit.objects.filter(
                    owner_type='employer', 
                    owner_id=employer.id, 
                    status='active'
                ).aggregate(Sum('amount'))['amount__sum'] or 0

                self.stdout.write(self.style.SUCCESS(
                    f"Successfully created {credit_amount} carbon credits for {email}"))
                self.stdout.write(self.style.SUCCESS(
                    f"Employer now has a total of {total_credits} active credits"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}")) 