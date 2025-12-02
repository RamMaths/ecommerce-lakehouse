"""
Factory Boy factories for generating test data.
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from .models import Tenant, Customer, Product, Order, OrderItem, Event, Subscription, Invoice

fake = Faker()


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Faker('company')
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-').replace(',', '')[:50])
    domain = factory.LazyAttribute(lambda obj: f"{obj.slug}.example.com")
    is_active = True
    settings = factory.LazyFunction(lambda: {
        'plan_type': fake.random_element(['starter', 'professional', 'enterprise']),
        'max_users': fake.random_int(min=10, max=1000),
        'features': fake.random_elements(['analytics', 'api_access', 'custom_domain', 'priority_support'], unique=True, length=2)
    })


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    tenant = factory.SubFactory(TenantFactory)
    email = factory.Sequence(lambda n: f'customer{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Faker('phone_number')
    is_active = factory.Faker('boolean', chance_of_getting_true=90)
    metadata = factory.LazyFunction(lambda: {
        'age': fake.random_int(min=18, max=75),
        'country': fake.country_code(),
        'signup_source': fake.random_element(['organic', 'paid_ad', 'referral', 'social']),
        'preferences': {
            'newsletter': fake.boolean(),
            'notifications': fake.boolean()
        }
    })


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    tenant = factory.SubFactory(TenantFactory)
    sku = factory.LazyAttribute(lambda obj: f"SKU-{fake.unique.random_number(digits=8)}")
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text', max_nb_chars=200)
    category = factory.Faker('random_element', elements=['Electronics', 'Clothing', 'Home', 'Books', 'Sports'])
    price = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=5, max=2000))))
    cost = factory.LazyAttribute(lambda obj: obj.price * Decimal('0.6'))
    stock_quantity = factory.Faker('random_int', min=0, max=500)
    is_active = factory.Faker('boolean', chance_of_getting_true=95)


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    tenant = factory.SubFactory(TenantFactory)
    customer = factory.SubFactory(CustomerFactory, tenant=factory.SelfAttribute('..tenant'))
    order_number = factory.LazyAttribute(lambda obj: f"ORD-{fake.unique.random_number(digits=10)}")
    status = factory.Faker('random_element', elements=['pending', 'processing', 'completed', 'cancelled'])
    subtotal = Decimal('0.00')
    tax = Decimal('0.00')
    shipping = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=0, max=50))))
    total = Decimal('0.00')
    order_date = factory.Faker('date_time_between', start_date='-180d', end_date='now', tzinfo=timezone.utc)
    completed_at = factory.LazyAttribute(
        lambda obj: obj.order_date + timedelta(days=fake.random_int(min=1, max=7)) if obj.status == 'completed' else None
    )
    metadata = factory.LazyFunction(lambda: {
        'payment_method': fake.random_element(['credit_card', 'paypal', 'bank_transfer']),
        'shipping_address': {
            'street': fake.street_address(),
            'city': fake.city(),
            'state': fake.state_abbr(),
            'zip': fake.zipcode(),
            'country': fake.country_code()
        }
    })


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory, tenant=factory.SelfAttribute('..order.tenant'))
    quantity = factory.Faker('random_int', min=1, max=5)
    unit_price = factory.LazyAttribute(lambda obj: obj.product.price)
    discount = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=0, max=20))))
    total = factory.LazyAttribute(lambda obj: (obj.unit_price * obj.quantity) - obj.discount)


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    tenant = factory.SubFactory(TenantFactory)
    customer = factory.SubFactory(CustomerFactory, tenant=factory.SelfAttribute('..tenant'))
    event_type = factory.Faker('random_element', elements=['page_view', 'product_view', 'search', 'add_to_cart', 'checkout', 'purchase'])
    event_data = factory.LazyFunction(lambda: {
        'url': fake.url(),
        'referrer': fake.url() if fake.boolean() else None,
        'product_id': str(fake.uuid4()) if fake.boolean() else None,
        'search_term': fake.word() if fake.boolean() else None
    })
    session_id = factory.LazyFunction(lambda: fake.uuid4())
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    tenant = factory.SubFactory(TenantFactory)
    customer = factory.SubFactory(CustomerFactory, tenant=factory.SelfAttribute('..tenant'))
    plan_name = factory.Faker('random_element', elements=['Basic', 'Pro', 'Premium', 'Enterprise'])
    status = factory.Faker('random_element', elements=['trial', 'active', 'cancelled', 'expired'])
    start_date = factory.Faker('date_between', start_date='-180d', end_date='today')
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=365) if obj.status in ['active', 'trial'] else obj.start_date + timedelta(days=fake.random_int(min=30, max=180))
    )
    monthly_amount = factory.Faker('random_element', elements=[Decimal('9.99'), Decimal('29.99'), Decimal('99.99'), Decimal('299.99')])
    billing_cycle = factory.Faker('random_element', elements=['monthly', 'yearly'])


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    tenant = factory.SubFactory(TenantFactory)
    customer = factory.SubFactory(CustomerFactory, tenant=factory.SelfAttribute('..tenant'))
    subscription = factory.SubFactory(SubscriptionFactory, tenant=factory.SelfAttribute('..tenant'), customer=factory.SelfAttribute('..customer'))
    invoice_number = factory.LazyAttribute(lambda obj: f"INV-{fake.unique.random_number(digits=10)}")
    amount = factory.LazyAttribute(lambda obj: obj.subscription.monthly_amount if obj.subscription else Decimal(str(fake.random_int(min=10, max=500))))
    status = factory.Faker('random_element', elements=['draft', 'sent', 'paid', 'overdue', 'cancelled'])
    issue_date = factory.Faker('date_between', start_date='-180d', end_date='today')
    due_date = factory.LazyAttribute(lambda obj: obj.issue_date + timedelta(days=30))
    paid_date = factory.LazyAttribute(
        lambda obj: obj.issue_date + timedelta(days=fake.random_int(min=1, max=30)) if obj.status == 'paid' else None
    )
