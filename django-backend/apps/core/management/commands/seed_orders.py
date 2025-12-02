"""
Management command to seed order and order item data.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Tenant, Customer, Product, Order, OrderItem
from decimal import Decimal
import random
from datetime import timedelta
from faker import Faker

fake = Faker()


class Command(BaseCommand):
    help = 'Seed order and order item data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-customer',
            type=int,
            default=5,
            help='Average number of orders per customer'
        )

    def handle(self, *args, **options):
        per_customer = options['per_customer']
        
        tenants = list(Tenant.objects.all())
        if not tenants:
            self.stdout.write(self.style.ERROR('No tenants found.'))
            return

        total_orders = 0
        total_items = 0
        batch_size = 500

        for tenant in tenants:
            customers = list(Customer.objects.filter(tenant=tenant))
            products = list(Product.objects.filter(tenant=tenant))
            
            if not customers or not products:
                self.stdout.write(f'  Skipping {tenant.name} - no customers or products')
                continue

            self.stdout.write(f'  Creating orders for {tenant.name}...')
            
            orders_batch = []
            items_batch = []
            
            for customer in customers:
                # Vary orders per customer (some have more, some less)
                num_orders = max(1, int(random.gauss(per_customer, per_customer * 0.3)))
                
                for _ in range(num_orders):
                    # Generate order date within last 180 days
                    days_ago = random.randint(0, 180)
                    order_date = timezone.now() - timedelta(days=days_ago)
                    
                    # Status distribution
                    status = random.choices(
                        ['completed', 'processing', 'pending', 'cancelled'],
                        weights=[80, 10, 5, 5]
                    )[0]
                    
                    order = Order(
                        tenant=tenant,
                        customer=customer,
                        order_number=f"ORD-{fake.unique.random_number(digits=10)}",
                        status=status,
                        order_date=order_date,
                        completed_at=order_date + timedelta(days=random.randint(1, 7)) if status == 'completed' else None,
                        subtotal=Decimal('0.00'),
                        tax=Decimal('0.00'),
                        shipping=Decimal(str(random.randint(0, 50))),
                        total=Decimal('0.00'),
                        metadata={
                            'payment_method': random.choice(['credit_card', 'paypal', 'bank_transfer']),
                            'shipping_address': {
                                'city': fake.city(),
                                'country': fake.country_code()
                            }
                        }
                    )
                    orders_batch.append(order)
                    
                    if len(orders_batch) >= batch_size:
                        Order.objects.bulk_create(orders_batch)
                        total_orders += len(orders_batch)
                        orders_batch = []

            # Create remaining orders
            if orders_batch:
                Order.objects.bulk_create(orders_batch)
                total_orders += len(orders_batch)

            # Now create order items for all orders
            self.stdout.write(f'  Creating order items for {tenant.name}...')
            orders = Order.objects.filter(tenant=tenant)
            
            for order in orders:
                # 1-5 items per order
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))
                
                order_subtotal = Decimal('0.00')
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    unit_price = product.price
                    discount = Decimal(str(random.randint(0, 20)))
                    item_total = (unit_price * quantity) - discount
                    
                    order_subtotal += item_total
                    
                    items_batch.append(OrderItem(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=discount,
                        total=item_total
                    ))
                    
                    if len(items_batch) >= batch_size:
                        OrderItem.objects.bulk_create(items_batch)
                        total_items += len(items_batch)
                        items_batch = []
                
                # Update order totals
                order.subtotal = order_subtotal
                order.tax = order_subtotal * Decimal('0.08')  # 8% tax
                order.total = order.subtotal + order.tax + order.shipping
                order.save(update_fields=['subtotal', 'tax', 'total'])

            # Create remaining items
            if items_batch:
                OrderItem.objects.bulk_create(items_batch)
                total_items += len(items_batch)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_orders:,} orders with {total_items:,} items'))
