"""
Management command to seed subscription data.
"""
from django.core.management.base import BaseCommand
from apps.core.models import Tenant, Customer, Subscription
from datetime import date, timedelta
from decimal import Decimal
import random
from faker import Faker

fake = Faker()


class Command(BaseCommand):
    help = 'Seed subscription data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rate',
            type=float,
            default=0.3,
            help='Percentage of customers with subscriptions (0.0-1.0)'
        )

    def handle(self, *args, **options):
        rate = options['rate']
        
        tenants = list(Tenant.objects.all())
        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found.'))
            return

        total_subscriptions = 0
        batch_size = 500

        plans = [
            {'name': 'Basic', 'amount': Decimal('9.99')},
            {'name': 'Pro', 'amount': Decimal('29.99')},
            {'name': 'Premium', 'amount': Decimal('99.99')},
            {'name': 'Enterprise', 'amount': Decimal('299.99')},
        ]

        for tenant in tenants:
            customers = list(Customer.objects.filter(tenant=tenant))
            
            if not customers:
                self.stdout.write(f'  Skipping {tenant.name} - no customers')
                continue

            # Select random customers for subscriptions
            num_subscriptions = int(len(customers) * rate)
            selected_customers = random.sample(customers, num_subscriptions)
            
            self.stdout.write(f'  Creating {num_subscriptions} subscriptions for {tenant.name}...')
            
            subscriptions_batch = []
            
            for customer in selected_customers:
                plan = random.choice(plans)
                
                # Start date within last 180 days
                start_date = date.today() - timedelta(days=random.randint(0, 180))
                
                # Status distribution
                status = random.choices(
                    ['active', 'trial', 'cancelled', 'expired'],
                    weights=[70, 10, 15, 5]
                )[0]
                
                # End date based on status
                if status in ['active', 'trial']:
                    end_date = start_date + timedelta(days=365)
                else:
                    end_date = start_date + timedelta(days=random.randint(30, 180))
                
                subscriptions_batch.append(Subscription(
                    tenant=tenant,
                    customer=customer,
                    plan_name=plan['name'],
                    status=status,
                    start_date=start_date,
                    end_date=end_date,
                    monthly_amount=plan['amount'],
                    billing_cycle=random.choice(['monthly', 'yearly'])
                ))
                
                if len(subscriptions_batch) >= batch_size:
                    Subscription.objects.bulk_create(subscriptions_batch)
                    total_subscriptions += len(subscriptions_batch)
                    subscriptions_batch = []

            # Create remaining subscriptions
            if subscriptions_batch:
                Subscription.objects.bulk_create(subscriptions_batch)
                total_subscriptions += len(subscriptions_batch)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_subscriptions:,} subscriptions'))
