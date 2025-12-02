# Quick Reference Guide

## Common Commands

### Django Backend

#### Setup & Start
```bash
cd django-backend
./scripts/setup.sh                                    # Initial setup
docker-compose up -d                                  # Start services
docker-compose down                                   # Stop services
docker-compose down -v                                # Stop and remove volumes
```

#### Data Management
```bash
# Seed all data
docker-compose exec django python manage.py seed_all --scale medium

# Seed with clean (delete existing data first)
docker-compose exec django python manage.py seed_all --scale medium --clean

# Seed individual models
docker-compose exec django python manage.py seed_tenants --count 8
docker-compose exec django python manage.py seed_customers --per-tenant 500
docker-compose exec django python manage.py seed_products --per-tenant 100
docker-compose exec django python manage.py seed_orders --per-customer 5
docker-compose exec django python manage.py seed_events --per-customer 50
docker-compose exec django python manage.py seed_subscriptions --rate 0.3
docker-compose exec django python manage.py seed_invoices
```

#### Database Operations
```bash
# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Django shell
docker-compose exec django python manage.py shell_plus

# Connect to PostgreSQL
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc

# Create DMS publication
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc \
  -c "CREATE PUBLICATION dms_publication FOR ALL TABLES;"

# Backup database
docker-compose exec postgres pg_dump -U lakehouse_user lakehouse_poc > backup.sql

# Restore database
docker-compose exec -T postgres psql -U lakehouse_user lakehouse_poc < backup.sql
```

#### Logs & Debugging
```bash
# View all logs
docker-compose logs -f

# View Django logs
docker-compose logs -f django

# View PostgreSQL logs
docker-compose logs -f postgres

# Check PostgreSQL status
docker-compose exec postgres pg_isready -U lakehouse_user
```

### Useful SQL Queries

#### Data Verification
```sql
-- Count records per table
SELECT 'tenants' as table_name, COUNT(*) FROM core_tenant
UNION ALL
SELECT 'customers', COUNT(*) FROM core_customer
UNION ALL
SELECT 'products', COUNT(*) FROM core_product
UNION ALL
SELECT 'orders', COUNT(*) FROM core_order
UNION ALL
SELECT 'order_items', COUNT(*) FROM core_orderitem
UNION ALL
SELECT 'events', COUNT(*) FROM core_event
UNION ALL
SELECT 'subscriptions', COUNT(*) FROM core_subscription
UNION ALL
SELECT 'invoices', COUNT(*) FROM core_invoice;

-- Check tenant distribution
SELECT 
    t.name,
    COUNT(DISTINCT c.id) as customers,
    COUNT(DISTINCT p.id) as products,
    COUNT(DISTINCT o.id) as orders
FROM core_tenant t
LEFT JOIN core_customer c ON c.tenant_id = t.id
LEFT JOIN core_product p ON p.tenant_id = t.id
LEFT JOIN core_order o ON o.tenant_id = t.id
GROUP BY t.name
ORDER BY customers DESC;
```

#### Business Metrics
```sql
-- Revenue by tenant (last 30 days)
SELECT 
    t.name,
    COUNT(DISTINCT o.id) as order_count,
    SUM(o.total) as total_revenue,
    AVG(o.total) as avg_order_value
FROM core_tenant t
LEFT JOIN core_order o ON o.tenant_id = t.id
WHERE o.status = 'completed'
  AND o.order_date >= NOW() - INTERVAL '30 days'
GROUP BY t.name
ORDER BY total_revenue DESC;

-- Customer acquisition by month
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as new_customers
FROM core_customer
GROUP BY month
ORDER BY month;

-- Top products by revenue
SELECT 
    p.name,
    p.category,
    COUNT(oi.id) as times_ordered,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.total) as total_revenue
FROM core_product p
JOIN core_orderitem oi ON oi.product_id = p.id
JOIN core_order o ON o.id = oi.order_id
WHERE o.status = 'completed'
GROUP BY p.id, p.name, p.category
ORDER BY total_revenue DESC
LIMIT 20;

-- Event funnel analysis
SELECT 
    event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT session_id) as unique_sessions
FROM core_event
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_type
ORDER BY event_count DESC;

-- MRR by tenant
SELECT 
    t.name,
    COUNT(s.id) as active_subscriptions,
    SUM(s.monthly_amount) as mrr,
    AVG(s.monthly_amount) as avg_subscription_value
FROM core_tenant t
LEFT JOIN core_subscription s ON s.tenant_id = t.id
WHERE s.status = 'active'
GROUP BY t.name
ORDER BY mrr DESC;

-- Invoice payment status
SELECT 
    status,
    COUNT(*) as invoice_count,
    SUM(amount) as total_amount
FROM core_invoice
GROUP BY status
ORDER BY invoice_count DESC;
```

#### Data Quality Checks
```sql
-- Check for orphaned records
SELECT 'customers without tenant' as issue, COUNT(*) 
FROM core_customer c 
LEFT JOIN core_tenant t ON t.id = c.tenant_id 
WHERE t.id IS NULL
UNION ALL
SELECT 'orders without customer', COUNT(*) 
FROM core_order o 
LEFT JOIN core_customer c ON c.id = o.customer_id 
WHERE c.id IS NULL
UNION ALL
SELECT 'order items without order', COUNT(*) 
FROM core_orderitem oi 
LEFT JOIN core_order o ON o.id = oi.order_id 
WHERE o.id IS NULL;

-- Check date ranges
SELECT 
    'customers' as table_name,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM core_customer
UNION ALL
SELECT 'orders', MIN(order_date), MAX(order_date)
FROM core_order
UNION ALL
SELECT 'events', MIN(created_at), MAX(created_at)
FROM core_event;

-- Check for duplicate emails per tenant
SELECT 
    tenant_id,
    email,
    COUNT(*) as count
FROM core_customer
GROUP BY tenant_id, email
HAVING COUNT(*) > 1;
```

### Python Shell Examples

```python
# Start shell
docker-compose exec django python manage.py shell_plus

# Query examples
from apps.core.models import *

# Get tenant with most customers
tenant = Tenant.objects.annotate(
    customer_count=Count('customers')
).order_by('-customer_count').first()

# Get revenue for a tenant
from django.db.models import Sum
revenue = Order.objects.filter(
    tenant=tenant,
    status='completed'
).aggregate(total=Sum('total'))

# Get conversion rate
from django.db.models import Q
events = Event.objects.filter(tenant=tenant)
page_views = events.filter(event_type='page_view').count()
purchases = events.filter(event_type='purchase').count()
conversion_rate = (purchases / page_views * 100) if page_views > 0 else 0

# Get customer lifetime value
customer = Customer.objects.first()
ltv = Order.objects.filter(
    customer=customer,
    status='completed'
).aggregate(total=Sum('total'))['total']

# Get active subscriptions
active_subs = Subscription.objects.filter(
    status='active'
).select_related('tenant', 'customer')
```

## Environment Variables

### Django Backend (.env)
```bash
# Database
DATABASE_NAME=lakehouse_poc
DATABASE_USER=lakehouse_user
DATABASE_PASSWORD=secure_password_change_me
DATABASE_HOST=postgres
DATABASE_PORT=5432

# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Data Generation
FAKER_SEED=12345
```

## Ports

- **Django**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **PostgreSQL**: localhost:5432

## Data Scales

| Scale  | Time to Seed | Total Records | Use Case                    |
|--------|--------------|---------------|-----------------------------|
| Small  | ~30 seconds  | ~17K          | Quick testing               |
| Medium | ~3-5 minutes | ~540K         | Demo and development        |
| Large  | ~10-15 min   | ~3M           | Performance testing         |

## Troubleshooting

### PostgreSQL won't start
```bash
# Check if port 5432 is already in use
lsof -i :5432

# Remove existing volumes and restart
docker-compose down -v
docker-compose up -d
```

### Django migrations fail
```bash
# Reset database
docker-compose down -v
docker-compose up -d
sleep 5
docker-compose exec django python manage.py migrate
```

### Slow data generation
- Use `--scale small` for testing
- Check Docker resources (CPU, memory)
- Ensure SSD storage for Docker volumes

### Out of memory
- Reduce batch sizes in seed commands
- Use smaller scale
- Increase Docker memory limit

## Next Steps After Setup

1. ✅ Verify data in Django admin
2. ✅ Run sample SQL queries
3. ✅ Create PostgreSQL publication for DMS
4. ✅ Document database schema
5. ⏳ Proceed to Terraform infrastructure
6. ⏳ Configure AWS DMS
7. ⏳ Set up Glue ETL jobs
8. ⏳ Create Athena queries
9. ⏳ Configure Lake Formation

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [AWS DMS Documentation](https://docs.aws.amazon.com/dms/)
- [Apache Hudi Documentation](https://hudi.apache.org/)
- [AWS Glue Documentation](https://docs.aws.amazon.com/glue/)
