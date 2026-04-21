from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser, EmployeeProfile, EmployerProfile
from django.utils.text import slugify
import secrets
import string

class Command(BaseCommand):
    help = "Create a user with specific role: employee, employer, bank_admin, or super_admin"

    def add_arguments(self, parser):
        parser.add_argument('--role', type=str, help='Role of the user (employee, employer, bank_admin, super_admin)')
        parser.add_argument('--email', type=str, help='Email of the user')
        parser.add_argument('--password', type=str, help='Password of the user')
        parser.add_argument('--first_name', type=str, help='First name of the user')
        parser.add_argument('--last_name', type=str, help='Last name of the user')
        parser.add_argument('--company_name', type=str, help='Company name (for employer)')
        parser.add_argument('--approved', action='store_true', help='Whether the user is pre-approved')

    def _generate_password(self, length=12):
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for i in range(length))

    def handle(self, *args, **options):
        # Get or prompt for required data
        role = options.get('role')
        if not role:
            available_roles = ['employee', 'employer', 'bank_admin', 'super_admin']
            self.stdout.write("Available roles: " + ", ".join(available_roles))
            role = input("Enter role: ").lower()
            if role not in available_roles:
                self.stderr.write(self.style.ERROR(f"Invalid role! Must be one of: {', '.join(available_roles)}"))
                return
        
        email = options.get('email')
        if not email:
            email = input("Enter email: ")
            
        password = options.get('password')
        if not password:
            self.stdout.write("Leave password blank to generate a secure password")
            password = input("Enter password (or leave blank): ")
            if not password:
                password = self._generate_password()
                self.stdout.write(f"Generated password: {password}")
        
        first_name = options.get('first_name')
        if not first_name:
            first_name = input("Enter first name: ")
            
        last_name = options.get('last_name')
        if not last_name:
            last_name = input("Enter last name: ")
            
        # Get additional data for employer
        company_name = None
        registration_number = None
        industry = None
        
        if role == 'employer':
            company_name = options.get('company_name')
            if not company_name:
                company_name = input("Enter company name: ")
            registration_number = input("Enter company registration number: ")
            industry = input("Enter industry: ")
        
        # Set employee's employer if role is employee
        employer_id = None
        if role == 'employee':
            if EmployerProfile.objects.exists():
                self.stdout.write("Available employers:")
                for idx, employer in enumerate(EmployerProfile.objects.all()):
                    self.stdout.write(f"{idx+1}. {employer.company_name}")
                
                employer_idx = int(input("Select employer (number): ")) - 1
                try:
                    employer_id = EmployerProfile.objects.all()[employer_idx].id
                except (IndexError, ValueError):
                    self.stderr.write(self.style.ERROR("Invalid employer selection!"))
                    return
            else:
                self.stderr.write(self.style.ERROR("No employers exist! Please create an employer first."))
                return
        
        # Flag for pre-approval
        is_approved = options.get('approved', False)
                
        try:
            with transaction.atomic():
                # Generate a username from email if not provided
                username = slugify(email.split('@')[0])
                
                # Create the user
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    approved=is_approved
                )
                
                # Set role flags
                if role == 'employee':
                    user.is_employee = True
                elif role == 'employer':
                    user.is_employer = True
                elif role == 'bank_admin':
                    user.is_bank_admin = True
                    user.is_staff = True  # Bank admins need admin site access
                elif role == 'super_admin':
                    user.is_super_admin = True
                    user.is_staff = True
                    user.is_superuser = True  # Super admins are Django superusers
                
                user.save()
                
                # Create profile based on role
                if role == 'employer':
                    EmployerProfile.objects.create(
                        user=user,
                        company_name=company_name,
                        registration_number=registration_number or f"REG-{secrets.token_hex(8).upper()}",
                        industry=industry or "Not specified",
                        approved=is_approved
                    )
                    self.stdout.write(self.style.SUCCESS(f"Employer '{company_name}' created successfully!"))
                
                elif role == 'employee':
                    employer = EmployerProfile.objects.get(id=employer_id)
                    EmployeeProfile.objects.create(
                        user=user,
                        employer=employer,
                        approved=is_approved
                    )
                    self.stdout.write(self.style.SUCCESS(f"Employee created successfully for {employer.company_name}!"))
                
                else:
                    self.stdout.write(self.style.SUCCESS(f"{role.capitalize()} created successfully!"))
                
                # Print summary
                self.stdout.write("\nUser details:")
                self.stdout.write(f"Email: {email}")
                self.stdout.write(f"Role: {role}")
                self.stdout.write(f"Password: {password}")
                if not is_approved:
                    self.stdout.write(self.style.WARNING("Note: User needs approval before they can log in"))
                else:
                    self.stdout.write(self.style.SUCCESS("User is pre-approved and can log in immediately"))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating user: {str(e)}"))
            raise 