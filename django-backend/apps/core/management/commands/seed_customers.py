"""
Management command to seed customer data.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Tenant, Customer
from faker import Faker
import uuid

fake = Faker()


class Command(BaseCommand):
    help = 'Seed customer data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-tenant',
            type=int,
            default=500,
            help='Number of customers per tenant'
        )

    def handle(self, *args, **options):
        per_tenant = options['per_tenant']
        tenants = list(Tenant.objects.all())

        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found. Run seed_tenants first.'))
            return

        total_customers = 0
        batch_size = 500
        global_counter = 0

        for tenant in tenants:
            self.stdout.write(f'  Creating {per_tenant} customers for {tenant.name}...')
            
            customers = []
            for i in range(per_tenant):
                # Generate unique email using counter
                email = f'customer{global_counter}@example.com'
                global_counter += 1
                
                customers.append(Customer(
                    tenant=tenant,
                    email=email,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    phone=fake.phone_number()[:50],  # Truncate to max length
                    is_active=fake.boolean(chance_of_getting_true=90),
                    metadata={
                        'age': fake.random_int(min=18, max=75),
                        'country': fake.country_code(),
                        'signup_source': fake.random_element(['organic', 'paid_ad', 'referral', 'social']),
                        'preferences': {
                            'newsletter': fake.boolean(),
                            'notifications': fake.boolean()
                        }
                    }
                ))
                
                if len(customers) >= batch_size:
                    Customer.objects.bulk_create(customers, batch_size=batch_size)
                    total_customers += len(customers)
                    customers = []
            
            # Create remaining customers
            if customers:
                Customer.objects.bulk_create(customers, batch_size=batch_size)
                total_customers += len(customers)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_customers:,} customers across {len(tenants)} tenants'))
