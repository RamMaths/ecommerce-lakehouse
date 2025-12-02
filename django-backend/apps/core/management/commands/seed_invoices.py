"""
Management command to seed invoice data.
"""
from django.core.management.base import BaseCommand
from apps.core.models import Tenant, Subscription, Invoice
from datetime import date, timedelta
from decimal import Decimal
import random
from faker import Faker

fake = Faker()


class Command(BaseCommand):
    help = 'Seed invoice data for subscriptions'

    def handle(self, *args, **options):
        tenants = list(Tenant.objects.all())
        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found.'))
            return

        total_invoices = 0
        batch_size = 500

        for tenant in tenants:
            subscriptions = list(Subscription.objects.filter(tenant=tenant))
            
            if not subscriptions:
                self.stdout.write(f'  Skipping {tenant.name} - no subscriptions')
                continue

            self.stdout.write(f'  Creating invoices for {tenant.name}...')
            
            invoices_batch = []
            
            for subscription in subscriptions:
                # Calculate number of invoices based on subscription duration
                start = subscription.start_date
                end = subscription.end_date or date.today()
                
                # Generate monthly invoices
                current_date = start
                invoice_count = 0
                
                while current_date <= end and invoice_count < 12:  # Max 12 invoices per subscription
                    # Status distribution
                    if subscription.status == 'active':
                        status = random.choices(
                            ['paid', 'sent', 'overdue'],
                            weights=[85, 10, 5]
                        )[0]
                    elif subscription.status == 'cancelled':
                        status = random.choice(['paid', 'cancelled'])
                    else:
                        status = random.choice(['paid', 'overdue'])
                    
                    issue_date = current_date
                    due_date = issue_date + timedelta(days=30)
                    paid_date = None
                    
                    if status == 'paid':
                        paid_date = issue_date + timedelta(days=random.randint(1, 25))
                    
                    invoices_batch.append(Invoice(
                        tenant=tenant,
                        customer=subscription.customer,
                        subscription=subscription,
                        invoice_number=f"INV-{fake.unique.random_number(digits=10)}",
                        amount=subscription.monthly_amount,
                        status=status,
                        issue_date=issue_date,
                        due_date=due_date,
                        paid_date=paid_date
                    ))
                    
                    if len(invoices_batch) >= batch_size:
                        Invoice.objects.bulk_create(invoices_batch)
                        total_invoices += len(invoices_batch)
                        invoices_batch = []
                    
                    # Move to next month
                    current_date = current_date + timedelta(days=30)
                    invoice_count += 1

            # Create remaining invoices
            if invoices_batch:
                Invoice.objects.bulk_create(invoices_batch)
                total_invoices += len(invoices_batch)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_invoices:,} invoices'))
