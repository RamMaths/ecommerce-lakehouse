"""
Master management command to seed all data.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from apps.core.models import Tenant, Customer, Product, Order, OrderItem, Event, Subscription, Invoice
import time


class Command(BaseCommand):
    help = 'Seed all data for the lakehouse POC'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scale',
            type=str,
            default='medium',
            choices=['small', 'medium', 'large'],
            help='Data volume scale'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete all existing data before seeding'
        )

    def handle(self, *args, **options):
        scale = options['scale']
        clean = options['clean']

        start_time = time.time()

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('  LAKEHOUSE POC - DATA SEEDING'))
        self.stdout.write(self.style.WARNING(f'  Scale: {scale.upper()}'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Define scale configurations
        scales = {
            'small': {
                'tenants': 5,
                'customers_per_tenant': 100,
                'products_per_tenant': 50,
                'orders_per_customer': 3,
                'events_per_customer': 20,
                'subscription_rate': 0.2,
            },
            'medium': {
                'tenants': 8,
                'customers_per_tenant': 800,
                'products_per_tenant': 100,
                'orders_per_customer': 8,
                'events_per_customer': 50,
                'subscription_rate': 0.3,
            },
            'large': {
                'tenants': 10,
                'customers_per_tenant': 2000,
                'products_per_tenant': 150,
                'orders_per_customer': 12,
                'events_per_customer': 100,
                'subscription_rate': 0.4,
            }
        }

        config = scales[scale]

        if clean:
            self.stdout.write(self.style.WARNING('\n🗑️  Cleaning existing data...'))
            with transaction.atomic():
                Invoice.objects.all().delete()
                Subscription.objects.all().delete()
                Event.objects.all().delete()
                OrderItem.objects.all().delete()
                Order.objects.all().delete()
                Product.objects.all().delete()
                Customer.objects.all().delete()
                Tenant.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ All data cleaned\n'))

        # Step 1: Seed Tenants
        self.stdout.write(self.style.HTTP_INFO('📊 Step 1/7: Seeding Tenants'))
        call_command('seed_tenants', count=config['tenants'])

        # Step 2: Seed Customers
        self.stdout.write(self.style.HTTP_INFO('\n👥 Step 2/7: Seeding Customers'))
        call_command('seed_customers', per_tenant=config['customers_per_tenant'])

        # Step 3: Seed Products
        self.stdout.write(self.style.HTTP_INFO('\n📦 Step 3/7: Seeding Products'))
        call_command('seed_products', per_tenant=config['products_per_tenant'])

        # Step 4: Seed Subscriptions
        self.stdout.write(self.style.HTTP_INFO('\n💳 Step 4/7: Seeding Subscriptions'))
        call_command('seed_subscriptions', rate=config['subscription_rate'])

        # Step 5: Seed Orders
        self.stdout.write(self.style.HTTP_INFO('\n🛒 Step 5/7: Seeding Orders'))
        call_command('seed_orders', per_customer=config['orders_per_customer'])

        # Step 6: Seed Events
        self.stdout.write(self.style.HTTP_INFO('\n📈 Step 6/7: Seeding Events'))
        call_command('seed_events', per_customer=config['events_per_customer'])

        # Step 7: Seed Invoices
        self.stdout.write(self.style.HTTP_INFO('\n🧾 Step 7/7: Seeding Invoices'))
        call_command('seed_invoices')

        # Summary
        elapsed_time = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  ✓ DATA SEEDING COMPLETED'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'  Tenants:        {Tenant.objects.count():,}')
        self.stdout.write(f'  Customers:      {Customer.objects.count():,}')
        self.stdout.write(f'  Products:       {Product.objects.count():,}')
        self.stdout.write(f'  Orders:         {Order.objects.count():,}')
        self.stdout.write(f'  Order Items:    {OrderItem.objects.count():,}')
        self.stdout.write(f'  Events:         {Event.objects.count():,}')
        self.stdout.write(f'  Subscriptions:  {Subscription.objects.count():,}')
        self.stdout.write(f'  Invoices:       {Invoice.objects.count():,}')
        self.stdout.write('')
        self.stdout.write(f'  Time elapsed:   {elapsed_time:.2f} seconds')
        self.stdout.write(self.style.SUCCESS('=' * 70))
