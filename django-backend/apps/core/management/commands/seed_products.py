"""
Management command to seed product data.
"""
from django.core.management.base import BaseCommand
from apps.core.factories import ProductFactory
from apps.core.models import Tenant, Product


class Command(BaseCommand):
    help = 'Seed product data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-tenant',
            type=int,
            default=100,
            help='Number of products per tenant'
        )

    def handle(self, *args, **options):
        per_tenant = options['per_tenant']
        tenants = list(Tenant.objects.all())

        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found. Run seed_tenants first.'))
            return

        total_products = 0
        batch_size = 500

        for tenant in tenants:
            self.stdout.write(f'  Creating {per_tenant} products for {tenant.name}...')
            
            products = []
            for i in range(per_tenant):
                products.append(ProductFactory.build(tenant=tenant))
                
                if len(products) >= batch_size:
                    Product.objects.bulk_create(products, batch_size=batch_size)
                    total_products += len(products)
                    products = []
            
            if products:
                Product.objects.bulk_create(products, batch_size=batch_size)
                total_products += len(products)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_products:,} products across {len(tenants)} tenants'))
