"""
Management command to seed event data.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Tenant, Customer, Event
from datetime import timedelta
import random
from faker import Faker
import uuid

fake = Faker()


class Command(BaseCommand):
    help = 'Seed event data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-customer',
            type=int,
            default=50,
            help='Average number of events per customer'
        )

    def handle(self, *args, **options):
        per_customer = options['per_customer']
        
        tenants = list(Tenant.objects.all())
        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found.'))
            return

        total_events = 0
        batch_size = 1000

        for tenant in tenants:
            customers = list(Customer.objects.filter(tenant=tenant))
            
            if not customers:
                self.stdout.write(f'  Skipping {tenant.name} - no customers')
                continue

            self.stdout.write(f'  Creating events for {tenant.name}...')
            
            events_batch = []
            
            for customer in customers:
                # Vary events per customer
                num_events = max(5, int(random.gauss(per_customer, per_customer * 0.4)))
                
                # Create sessions (groups of events)
                num_sessions = max(1, num_events // 10)
                
                for session_num in range(num_sessions):
                    session_id = str(uuid.uuid4())
                    events_in_session = num_events // num_sessions
                    
                    # Session start time
                    days_ago = random.randint(0, 180)
                    session_start = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
                    
                    # Event funnel: page_view -> product_view -> add_to_cart -> checkout -> purchase
                    event_types = ['page_view'] * 5 + ['product_view'] * 3 + ['add_to_cart', 'checkout']
                    if random.random() < 0.3:  # 30% conversion
                        event_types.append('purchase')
                    
                    for i in range(min(events_in_session, len(event_types))):
                        event_time = session_start + timedelta(minutes=i * 2)
                        
                        events_batch.append(Event(
                            tenant=tenant,
                            customer=customer if random.random() < 0.7 else None,  # 30% anonymous
                            event_type=event_types[i],
                            event_data={
                                'url': fake.url(),
                                'product_id': str(uuid.uuid4()) if 'product' in event_types[i] else None,
                                'search_term': fake.word() if event_types[i] == 'search' else None
                            },
                            session_id=session_id,
                            ip_address=fake.ipv4(),
                            user_agent=fake.user_agent(),
                            created_at=event_time
                        ))
                        
                        if len(events_batch) >= batch_size:
                            Event.objects.bulk_create(events_batch)
                            total_events += len(events_batch)
                            events_batch = []

            # Create remaining events
            if events_batch:
                Event.objects.bulk_create(events_batch)
                total_events += len(events_batch)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_events:,} events'))
