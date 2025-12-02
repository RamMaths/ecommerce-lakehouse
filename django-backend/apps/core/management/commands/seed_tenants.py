"""
Management command to seed tenant data.
"""
from django.core.management.base import BaseCommand
from apps.core.factories import TenantFactory
from apps.core.models import Tenant


class Command(BaseCommand):
    help = 'Seed tenant data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=8,
            help='Number of tenants to create'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing tenants before seeding'
        )

    def handle(self, *args, **options):
        count = options['count']
        clean = options['clean']

        if clean:
            self.stdout.write('Cleaning existing tenants...')
            Tenant.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Existing tenants deleted'))

        self.stdout.write(f'Creating {count} tenants...')
        
        # Define tenant profiles
        profiles = [
            {'name': 'TechCorp Enterprise', 'plan': 'enterprise', 'max_users': 1000},
            {'name': 'Global Solutions Inc', 'plan': 'enterprise', 'max_users': 800},
            {'name': 'MidMarket Retail Co', 'plan': 'professional', 'max_users': 300},
            {'name': 'Digital Services Ltd', 'plan': 'professional', 'max_users': 250},
            {'name': 'StartUp Innovations', 'plan': 'professional', 'max_users': 200},
            {'name': 'Small Business Shop', 'plan': 'starter', 'max_users': 50},
            {'name': 'Local Store Group', 'plan': 'starter', 'max_users': 75},
            {'name': 'Boutique Commerce', 'plan': 'starter', 'max_users': 40},
        ]

        tenants = []
        for i in range(min(count, len(profiles))):
            profile = profiles[i]
            tenant = TenantFactory(
                name=profile['name'],
                settings={
                    'plan_type': profile['plan'],
                    'max_users': profile['max_users'],
                    'features': self._get_features(profile['plan'])
                }
            )
            tenants.append(tenant)
            self.stdout.write(f'  ✓ Created: {tenant.name} ({tenant.slug})')

        # Create additional random tenants if count > profiles
        for i in range(len(profiles), count):
            tenant = TenantFactory()
            tenants.append(tenant)
            self.stdout.write(f'  ✓ Created: {tenant.name} ({tenant.slug})')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {len(tenants)} tenants'))

    def _get_features(self, plan):
        features_map = {
            'enterprise': ['analytics', 'api_access', 'custom_domain', 'priority_support', 'sso'],
            'professional': ['analytics', 'api_access', 'custom_domain'],
            'starter': ['analytics']
        }
        return features_map.get(plan, ['analytics'])
