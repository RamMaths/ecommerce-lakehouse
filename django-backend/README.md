# Django Backend - Lakehouse POC

Multi-tenant Django application that generates realistic e-commerce data for AWS DMS replication and lakehouse architecture demonstration.

## Quick Start

### 1. Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your configuration (optional for local development)
```

### 2. Start Services

```bash
# Build and start containers
docker-compose up -d

# Wait for PostgreSQL to be ready (check with)
docker-compose logs postgres
```

### 3. Run Migrations

```bash
# Create database tables
docker-compose exec django python manage.py migrate

# Create superuser for admin access
docker-compose exec django python manage.py createsuperuser
```

### 4. Seed Data

```bash
# Seed all data with medium scale (recommended)
docker-compose exec django python manage.py seed_all --scale medium

# Or choose different scales:
# --scale small   : ~5K records (fast, for testing)
# --scale medium  : ~50K records (balanced, for demo)
# --scale large   : ~200K records (comprehensive, for performance testing)

# Clean and reseed
docker-compose exec django python manage.py seed_all --scale medium --clean
```

### 5. Access Services

- **Django Admin**: http://localhost:8000/admin
- **PostgreSQL**: localhost:5432
  - Database: `lakehouse_poc`
  - User: `lakehouse_user`
  - Password: `secure_password`

## Data Models

### Tenant
Client organizations in the multi-tenant system
- 8-10 tenants with varying sizes (enterprise, mid-market, small business)

### Customer
End users per tenant
- 100-2000 customers per tenant depending on scale
- Realistic demographics and metadata

### Product
Items/services offered by each tenant
- 50-150 products per tenant
- Categories: Electronics, Clothing, Home, Books, Sports
- Price range: $5 - $2,000

### Order & OrderItem
Purchase transactions
- 3-12 orders per customer on average
- 1-5 items per order
- Status distribution: 80% completed, 10% processing, 5% pending, 5% cancelled

### Event
User activity tracking
- 20-100 events per customer
- Types: page_view, product_view, search, add_to_cart, checkout, purchase
- Sessionized with realistic conversion funnels

### Subscription
Recurring revenue tracking
- 20-40% of customers have subscriptions
- Plans: Basic ($9.99), Pro ($29.99), Premium ($99.99), Enterprise ($299.99)
- Status: active, trial, cancelled, expired

### Invoice
Billing records
- Generated monthly for active subscriptions
- Status: draft, sent, paid, overdue, cancelled

## Management Commands

### Individual Seed Commands

```bash
# Seed specific data types
docker-compose exec django python manage.py seed_tenants --count 8
docker-compose exec django python manage.py seed_customers --per-tenant 500
docker-compose exec django python manage.py seed_products --per-tenant 100
docker-compose exec django python manage.py seed_orders --per-customer 5
docker-compose exec django python manage.py seed_events --per-customer 50
docker-compose exec django python manage.py seed_subscriptions --rate 0.3
docker-compose exec django python manage.py seed_invoices
```

### Master Seed Command

```bash
# Seed everything at once
docker-compose exec django python manage.py seed_all --scale medium

# Options:
#   --scale {small|medium|large}  Data volume
#   --clean                       Delete existing data first
```

## PostgreSQL Configuration for DMS

The PostgreSQL instance is pre-configured for AWS DMS replication:

- **WAL Level**: `logical` (required for CDC)
- **Max Replication Slots**: 4
- **Max WAL Senders**: 4
- **Replication User**: Main user has replication privileges

### Create Publication (After Migrations)

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc

# Create publication for all tables
CREATE PUBLICATION dms_publication FOR ALL TABLES;

# Verify
\dRp+
```

## Database Schema

All tables use:
- **UUID Primary Keys**: Better for distributed systems
- **Timestamps**: `created_at` and `updated_at` on all tables
- **Indexes**: Optimized for multi-tenant queries and DMS replication
- **Partitioning Ready**: `tenant_id` indexed on all tables

### Table Naming Convention

- `core_tenant`
- `core_customer`
- `core_product`
- `core_order`
- `core_orderitem`
- `core_event`
- `core_subscription`
- `core_invoice`

## Data Characteristics

### Time Distribution
- **Historical Range**: 180 days (6 months)
- **Distribution**: More recent data is denser
- **Patterns**: Weekly seasonality, monthly peaks, growth trends

### Multi-Tenant Profiles

**Enterprise (2 tenants)**
- 1,000-2,000 customers
- 150+ products
- High order volume
- High event activity

**Mid-Market (3 tenants)**
- 500-1,000 customers
- 100-150 products
- Medium order volume
- Medium event activity

**Small Business (3-5 tenants)**
- 100-300 customers
- 50-80 products
- Lower order volume
- Lower event activity

## Development

### Run Django Shell

```bash
docker-compose exec django python manage.py shell_plus
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f django
docker-compose logs -f postgres
```

### Stop Services

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (deletes database)
docker-compose down -v
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U lakehouse_user

# Check PostgreSQL logs
docker-compose logs postgres
```

### Django Migration Issues

```bash
# Reset migrations (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose exec django python manage.py migrate
```

### Slow Data Generation

- Use `--scale small` for faster testing
- Batch operations are optimized (500-1000 records per batch)
- Expected times:
  - Small: ~30 seconds
  - Medium: ~3-5 minutes
  - Large: ~10-15 minutes

## Next Steps

After seeding data:

1. **Verify Data**: Check Django admin or connect to PostgreSQL
2. **Create Publication**: Run the SQL command above
3. **Export Schema**: Document table structures for Terraform
4. **Configure DMS**: Set up AWS DMS source endpoint
5. **Test Replication**: Verify CDC with sample updates

## Sample Queries

```sql
-- Revenue by tenant
SELECT 
    t.name,
    COUNT(DISTINCT o.id) as order_count,
    SUM(o.total) as total_revenue
FROM core_tenant t
LEFT JOIN core_order o ON o.tenant_id = t.id
WHERE o.status = 'completed'
GROUP BY t.name
ORDER BY total_revenue DESC;

-- Customer acquisition by month
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as new_customers
FROM core_customer
GROUP BY month
ORDER BY month;

-- Event funnel
SELECT 
    event_type,
    COUNT(*) as event_count
FROM core_event
GROUP BY event_type
ORDER BY event_count DESC;

-- MRR by tenant
SELECT 
    t.name,
    SUM(s.monthly_amount) as mrr
FROM core_tenant t
LEFT JOIN core_subscription s ON s.tenant_id = t.id
WHERE s.status = 'active'
GROUP BY t.name
ORDER BY mrr DESC;
```
