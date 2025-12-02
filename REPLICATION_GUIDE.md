# Environment Replication Guide

Complete step-by-step guide to replicate this lakehouse POC environment on any machine.

## Prerequisites Check

Before starting, ensure you have:

- [ ] Docker Desktop installed and running
- [ ] At least 10GB free disk space
- [ ] 4GB+ RAM available for Docker
- [ ] Ports 5432 and 8000 available
- [ ] Git installed

### Verify Prerequisites

```bash
# Check Docker is installed and running
docker --version
docker-compose --version
docker ps

# Check available disk space
df -h

# Check if ports are available
lsof -i :5432
lsof -i :8000
# (Should return nothing if ports are free)
```

## Step 1: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd lakehouse-poc

# Verify structure
ls -la
# You should see: django-backend/, docs/, README.md, etc.
```

## Step 2: Configure Environment (Optional)

The default configuration works for local development, but you can customize:

```bash
cd django-backend

# Copy environment template
cp .env.example .env

# Edit if needed (optional)
nano .env  # or use your preferred editor

# Default values:
# DATABASE_NAME=lakehouse_poc
# DATABASE_USER=lakehouse_user
# DATABASE_PASSWORD=secure_password
# DATABASE_HOST=postgres
# DATABASE_PORT=5432
```

## Step 3: Start Docker Services

```bash
# Make sure you're in django-backend directory
cd django-backend

# Start PostgreSQL and Django containers
docker-compose up -d

# Verify containers are running
docker-compose ps

# Expected output:
# NAME                  STATUS    PORTS
# lakehouse_postgres    Up        0.0.0.0:5432->5432/tcp
# lakehouse_django      Up        0.0.0.0:8000->8000/tcp
```

### Wait for PostgreSQL to be Ready

```bash
# Check PostgreSQL health (repeat until it says "accepting connections")
docker-compose logs postgres | tail -20

# Or use the health check
docker-compose exec postgres pg_isready -U lakehouse_user

# Expected output: "postgres:5432 - accepting connections"
```

## Step 4: Initialize Database

### Create Database Schema

```bash
# Run Django migrations to create tables
docker-compose exec django python manage.py migrate

# Expected output:
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, core, sessions
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   Applying auth.0001_initial... OK
#   ...
#   Applying core.0001_initial... OK
```

### Verify Tables Were Created

```bash
# List all tables
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "\dt"

# You should see 8 core tables:
# core_tenant
# core_customer
# core_product
# core_order
# core_orderitem
# core_event
# core_subscription
# core_invoice
```

## Step 5: Create Admin User

```bash
# Create Django superuser
docker-compose exec django python manage.py createsuperuser

# Interactive prompts:
# Username: admin
# Email address: admin@example.com
# Password: ******** (minimum 8 characters)
# Password (again): ********
# Bypass password validation? [y/N]: y (if using simple password)

# Expected output: "Superuser created successfully."
```

## Step 6: Generate Sample Data

### Option A: Medium Scale (Recommended)

```bash
# Generate ~540K records (takes ~2-3 minutes)
docker-compose exec django python manage.py seed_all --scale medium

# Watch the progress:
# 📊 Step 1/7: Seeding Tenants
# 👥 Step 2/7: Seeding Customers
# 📦 Step 3/7: Seeding Products
# 💳 Step 4/7: Seeding Subscriptions
# 🛒 Step 5/7: Seeding Orders
# 📈 Step 6/7: Seeding Events
# 🧾 Step 7/7: Seeding Invoices
```

### Option B: Small Scale (For Testing)

```bash
# Generate ~17K records (takes ~30 seconds)
docker-compose exec django python manage.py seed_all --scale small
```

### Option C: Large Scale (For Performance Testing)

```bash
# Generate ~3M records (takes ~10-15 minutes)
docker-compose exec django python manage.py seed_all --scale large
```

### Verify Data Was Created

```bash
# Check record counts
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "
SELECT 
  'tenants' as table_name, COUNT(*) as count FROM core_tenant
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
"

# Expected output (medium scale):
#   table_name   | count
# ---------------+--------
#  tenants       |      8
#  customers     |   6400
#  products      |    800
#  orders        |  47750
#  order_items   | 142852
#  events        | 293339
#  subscriptions |   1920
#  invoices      |  19694
```

## Step 7: Configure PostgreSQL for DMS

```bash
# Create publication for AWS DMS replication
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc \
  -c "CREATE PUBLICATION dms_publication FOR ALL TABLES;"

# Expected output: "CREATE PUBLICATION"

# Verify publication
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "\dRp+"

# Expected output:
#                            Publication dms_publication
#      Owner      | All tables | Inserts | Updates | Deletes | Truncates
# ----------------+------------+---------+---------+---------+-----------
#  lakehouse_user | t          | t       | t       | t       | t
```

## Step 8: Verify Complete Setup

### Test Django Admin

```bash
# Open Django admin in browser
open http://localhost:8000/admin
# Or manually navigate to: http://localhost:8000/admin

# Login with:
# Username: admin
# Password: (the password you created)

# You should see all 8 models:
# - Tenants
# - Customers
# - Products
# - Orders
# - Order Items
# - Events
# - Subscriptions
# - Invoices
```

### Test Database Connection

```bash
# Connect to PostgreSQL from host
psql -h localhost -p 5432 -U lakehouse_user -d lakehouse_poc
# Password: secure_password

# Run a test query
SELECT name, slug FROM core_tenant;

# Exit psql
\q
```

### Test Sample Business Query

```bash
# Revenue by tenant
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "
SELECT 
    t.name,
    COUNT(DISTINCT o.id) as order_count,
    ROUND(SUM(o.total)::numeric, 2) as total_revenue
FROM core_tenant t
LEFT JOIN core_order o ON o.tenant_id = t.id
WHERE o.status = 'completed'
GROUP BY t.name
ORDER BY total_revenue DESC
LIMIT 5;
"
```

## Step 9: Backup Configuration (Optional)

```bash
# Backup database
docker-compose exec postgres pg_dump -U lakehouse_user lakehouse_poc > backup_$(date +%Y%m%d).sql

# Backup environment
cp .env .env.backup

# Create a snapshot of Docker volumes (optional)
docker-compose down
docker run --rm -v lakehouse_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .
docker-compose up -d
```

## Verification Checklist

After completing all steps, verify:

- [ ] Docker containers are running (`docker-compose ps`)
- [ ] PostgreSQL is accepting connections
- [ ] Django admin is accessible at http://localhost:8000/admin
- [ ] All 8 tables exist in database
- [ ] Data is populated (check counts)
- [ ] DMS publication is created
- [ ] Can login to Django admin
- [ ] Can query database from host machine

## Troubleshooting

### Issue: Containers won't start

```bash
# Check Docker is running
docker info

# Check logs
docker-compose logs

# Restart Docker Desktop and try again
docker-compose down
docker-compose up -d
```

### Issue: Port already in use

```bash
# Find what's using the port
lsof -i :5432
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
# Edit docker-compose.yml and change:
# ports:
#   - "5433:5432"  # Changed from 5432:5432
```

### Issue: Migrations fail

```bash
# Reset everything
docker-compose down -v
docker-compose up -d
sleep 10
docker-compose exec django python manage.py migrate
```

### Issue: Data seeding fails

```bash
# Clean and retry
docker-compose exec django python manage.py seed_all --scale small --clean

# If still fails, check logs
docker-compose logs django
```

### Issue: Out of disk space

```bash
# Clean Docker system
docker system prune -a --volumes

# Increase Docker Desktop disk allocation
# Docker Desktop → Settings → Resources → Disk image size → Increase to 20GB+
```

## Daily Operations

### Start Environment

```bash
cd lakehouse-poc/django-backend
docker-compose up -d
```

### Stop Environment

```bash
docker-compose down
# Add -v to also remove volumes (deletes data)
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f django
docker-compose logs -f postgres
```

### Reseed Data

```bash
# Clean and reseed
docker-compose exec django python manage.py seed_all --scale medium --clean
```

### Access Django Shell

```bash
docker-compose exec django python manage.py shell_plus
```

### Run Custom SQL

```bash
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc
```

## Next Steps

Once your environment is replicated and verified:

1. ✅ Explore data in Django admin
2. ✅ Run sample SQL queries (see [Quick Reference](./QUICK_REFERENCE.md))
3. ✅ Test CDC by updating records
4. ✅ Document database schema for Terraform
5. ⏳ Proceed to Terraform infrastructure (Step 2)

## Support

If you encounter issues not covered here:

1. Check [Quick Reference Guide](./QUICK_REFERENCE.md)
2. Review [Django Backend README](./django-backend/README.md)
3. Check Docker logs: `docker-compose logs`
4. Verify prerequisites are met
5. Try with `--scale small` first

## Success Criteria

Your environment is successfully replicated when:

✅ All Docker containers are running
✅ Django admin is accessible
✅ Database contains sample data
✅ PostgreSQL publication exists
✅ Can run SQL queries successfully
✅ No errors in logs

---

**Estimated Time:** 15-20 minutes (including data generation)

**Disk Space Required:** ~5-10GB

**RAM Required:** 4GB+ recommended
