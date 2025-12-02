# Django Backend Implementation Plan
## Lakehouse POC - Multi-Tenant Data Source

---

## 1. Project Overview

**Purpose**: Create a multi-tenant Django application that simulates a SaaS e-commerce platform to generate realistic data for AWS DMS replication and lakehouse architecture demonstration.

**Target**: Showcase CDC (Change Data Capture), multi-tenant data isolation, and historical metrics across different clients.

---

## 2. Technical Stack

- **Framework**: Django 4.2+
- **Database**: PostgreSQL 15+
- **Container**: Docker + Docker Compose
- **Python**: 3.11+
- **Additional Libraries**:
  - `psycopg2-binary` - PostgreSQL adapter
  - `faker` - Synthetic data generation
  - `django-extensions` - Enhanced management commands
  - `django-tenant-schemas` or manual tenant isolation
  - `factory-boy` - Test data factories

---

## 3. Database Schema Design

### 3.1 Core Models

#### Tenant Model
```python
- id (UUID, PK)
- name (String, unique)
- slug (String, unique, indexed)
- domain (String, optional)
- created_at (DateTime)
- updated_at (DateTime)
- is_active (Boolean)
- settings (JSONField) # Plan type, features, etc.
```

#### Customer Model
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- email (String, indexed)
- first_name (String)
- last_name (String)
- phone (String, nullable)
- created_at (DateTime)
- updated_at (DateTime)
- is_active (Boolean)
- metadata (JSONField) # Demographics, preferences
```

#### Product Model
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- sku (String, indexed)
- name (String)
- description (Text)
- category (String, indexed)
- price (Decimal)
- cost (Decimal)
- stock_quantity (Integer)
- created_at (DateTime)
- updated_at (DateTime)
- is_active (Boolean)
```

#### Order Model
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- customer_id (FK to Customer, indexed)
- order_number (String, unique, indexed)
- status (String, choices: pending/processing/completed/cancelled)
- subtotal (Decimal)
- tax (Decimal)
- shipping (Decimal)
- total (Decimal)
- order_date (DateTime, indexed)
- completed_at (DateTime, nullable)
- created_at (DateTime)
- updated_at (DateTime)
- metadata (JSONField) # Payment method, shipping address
```

#### OrderItem Model
```python
- id (UUID, PK)
- order_id (FK to Order, indexed)
- product_id (FK to Product, indexed)
- quantity (Integer)
- unit_price (Decimal)
- discount (Decimal, default=0)
- total (Decimal)
- created_at (DateTime)
- updated_at (DateTime)
```

#### Event Model (User Activity Tracking)
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- customer_id (FK to Customer, nullable, indexed)
- event_type (String, indexed) # page_view, click, search, add_to_cart
- event_data (JSONField) # URL, product_id, search_term, etc.
- session_id (String, indexed)
- ip_address (GenericIPAddress)
- user_agent (Text)
- created_at (DateTime, indexed)
```

#### Subscription Model
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- customer_id (FK to Customer, indexed)
- plan_name (String)
- status (String, choices: active/cancelled/expired/trial)
- start_date (Date, indexed)
- end_date (Date, nullable, indexed)
- monthly_amount (Decimal)
- billing_cycle (String) # monthly, yearly
- created_at (DateTime)
- updated_at (DateTime)
```

#### Invoice Model
```python
- id (UUID, PK)
- tenant_id (FK to Tenant, indexed)
- customer_id (FK to Customer, indexed)
- subscription_id (FK to Subscription, nullable, indexed)
- invoice_number (String, unique, indexed)
- amount (Decimal)
- status (String, choices: draft/sent/paid/overdue/cancelled)
- issue_date (Date, indexed)
- due_date (Date, indexed)
- paid_date (Date, nullable)
- created_at (DateTime)
- updated_at (DateTime)
```

### 3.2 Indexes Strategy

**Critical Indexes for DMS and Analytics**:
- `tenant_id` on all tables (partition key simulation)
- Timestamp fields (`created_at`, `updated_at`, `order_date`)
- Foreign keys
- Status fields for filtering
- Composite indexes: `(tenant_id, created_at)`, `(tenant_id, status)`

---

## 4. Project Structure

```
django-backend/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── manage.py
├── config/                      # Project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   └── core/                    # Main application
│       ├── __init__.py
│       ├── models.py            # All models
│       ├── admin.py             # Django admin config
│       ├── apps.py
│       ├── managers.py          # Custom model managers
│       ├── factories.py         # Factory Boy factories
│       └── management/
│           └── commands/
│               ├── seed_tenants.py
│               ├── seed_customers.py
│               ├── seed_products.py
│               ├── seed_orders.py
│               ├── seed_events.py
│               ├── seed_subscriptions.py
│               ├── seed_all.py
│               ├── simulate_activity.py  # Ongoing CDC changes
│               └── cleanup_data.py
├── scripts/
│   ├── init_db.sh
│   ├── backup_db.sh
│   └── generate_sample_queries.sql
└── docs/
    ├── API.md
    ├── DATA_GENERATION.md
    └── METRICS_EXAMPLES.md
```

---

## 5. Data Generation Strategy

### 5.1 Seed Data Volumes

**Target Data for POC**:
- **Tenants**: 8-10 (varying sizes: small, medium, large)
- **Customers**: 5,000-10,000 total (distributed across tenants)
- **Products**: 500-1,000 per tenant
- **Orders**: 50,000-100,000 total (6 months historical)
- **OrderItems**: 150,000-300,000 (avg 3 items per order)
- **Events**: 500,000-1,000,000 (high volume activity logs)
- **Subscriptions**: 2,000-5,000
- **Invoices**: 10,000-20,000

### 5.2 Tenant Profiles

Create realistic tenant variations:

1. **Enterprise Tenant** (2 tenants)
   - 2,000+ customers
   - 200+ products
   - 20,000+ orders
   - High event volume

2. **Mid-Market Tenant** (3 tenants)
   - 500-1,000 customers
   - 100-150 products
   - 5,000-10,000 orders
   - Medium event volume

3. **Small Business Tenant** (3-5 tenants)
   - 100-300 customers
   - 50-80 products
   - 1,000-3,000 orders
   - Low-medium event volume

### 5.3 Time Distribution

- **Historical Range**: 6 months (180 days)
- **Distribution**: 
  - 60% of data in last 3 months
  - 30% in months 4-5
  - 10% in month 6
- **Patterns**:
  - Weekly seasonality (weekends vs weekdays)
  - Monthly peaks (end of month)
  - Growth trends (increasing over time)

### 5.4 Data Realism Features

- **Customer Behavior**:
  - Repeat customers (70% of orders from 30% of customers)
  - Customer lifecycle (new → active → churned)
  - Realistic email domains, names, phone numbers

- **Product Catalog**:
  - Categories: Electronics, Clothing, Home, Books, Sports
  - Price ranges: $5 - $2,000
  - Stock levels with occasional out-of-stock

- **Order Patterns**:
  - Status distribution: 80% completed, 10% processing, 5% cancelled, 5% pending
  - Average order value: $50-$200
  - Seasonal variations

- **Events**:
  - Conversion funnel: page_view → product_view → add_to_cart → checkout → purchase
  - Bounce rates, session durations
  - Anonymous vs authenticated users

---

## 6. Management Commands Implementation

### 6.1 seed_all.py
Master command that orchestrates all seeding in correct order:
1. Tenants
2. Customers
3. Products
4. Subscriptions
5. Orders & OrderItems
6. Events
7. Invoices

**Options**:
- `--tenants N` - Number of tenants
- `--scale [small|medium|large]` - Data volume
- `--start-date YYYY-MM-DD` - Historical start
- `--clean` - Clear existing data first

### 6.2 simulate_activity.py
Continuous data generation for CDC demonstration:
- Create new orders every few seconds
- Update order statuses
- Generate real-time events
- Update product stock levels
- Create new customers
- Process payments (update invoices)

**Options**:
- `--duration MINUTES` - How long to run
- `--rate N` - Operations per minute
- `--operations [orders|events|updates|all]`

### 6.3 Individual Seed Commands
Each model has dedicated seeding command with:
- Progress bars
- Batch inserts for performance
- Referential integrity checks
- Configurable volumes

---

## 7. Docker Configuration

### 7.1 docker-compose.yml Services

```yaml
services:
  postgres:
    - PostgreSQL 15
    - Port 5432
    - Volume for persistence
    - Environment variables for credentials
    
  django:
    - Python 3.11
    - Depends on postgres
    - Port 8000
    - Volume mounts for code
    - Auto-reload for development
    
  pgadmin (optional):
    - Web UI for database inspection
    - Port 5050
```

### 7.2 Environment Variables

```
DATABASE_NAME=lakehouse_poc
DATABASE_USER=lakehouse_user
DATABASE_PASSWORD=secure_password
DATABASE_HOST=postgres
DATABASE_PORT=5432
DJANGO_SECRET_KEY=generated_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## 8. Implementation Phases

### Phase 1: Project Setup (Day 1)
- [ ] Initialize Django project
- [ ] Configure Docker and docker-compose
- [ ] Set up PostgreSQL connection
- [ ] Create project structure
- [ ] Install dependencies

### Phase 2: Models & Migrations (Day 1-2)
- [ ] Define all models in models.py
- [ ] Add model managers and custom methods
- [ ] Create and run migrations
- [ ] Configure Django admin
- [ ] Add model validations

### Phase 3: Data Factories (Day 2)
- [ ] Create Factory Boy factories for each model
- [ ] Add realistic data generation logic
- [ ] Test factory outputs
- [ ] Document factory usage

### Phase 4: Seed Commands (Day 2-3)
- [ ] Implement individual seed commands
- [ ] Create master seed_all command
- [ ] Add progress tracking
- [ ] Optimize bulk inserts
- [ ] Test with various scales

### Phase 5: Activity Simulation (Day 3)
- [ ] Implement simulate_activity command
- [ ] Add CDC-friendly operations (INSERT/UPDATE/DELETE)
- [ ] Create realistic activity patterns
- [ ] Add logging and monitoring

### Phase 6: Testing & Validation (Day 4)
- [ ] Verify data quality
- [ ] Check referential integrity
- [ ] Test multi-tenant isolation
- [ ] Validate data distributions
- [ ] Performance testing

### Phase 7: Documentation (Day 4)
- [ ] README with setup instructions
- [ ] Data generation guide
- [ ] Sample SQL queries for metrics
- [ ] Architecture diagrams
- [ ] Troubleshooting guide

---

## 9. Key Metrics to Enable

The generated data should support these analytics queries:

### Revenue Metrics
- Total revenue by tenant over time
- Average order value by tenant
- Revenue growth rate (MoM, QoQ)
- Product category performance

### Customer Metrics
- Customer acquisition by tenant
- Customer lifetime value
- Retention rates
- Churn analysis

### Product Metrics
- Best-selling products by tenant
- Inventory turnover
- Product profitability
- Category trends

### Behavioral Metrics
- Conversion funnel analysis
- Session duration trends
- Cart abandonment rates
- User engagement scores

### Subscription Metrics
- MRR (Monthly Recurring Revenue)
- Subscription churn
- Plan distribution
- Payment success rates

---

## 10. DMS Preparation Considerations

### 10.1 Database Configuration
- Enable logical replication in PostgreSQL
- Configure WAL level to 'logical'
- Set appropriate retention
- Create replication user with proper permissions

### 10.2 Table Design for DMS
- Use UUID primary keys (better for distributed systems)
- Include `created_at` and `updated_at` on all tables
- Avoid complex triggers (can interfere with DMS)
- Use standard PostgreSQL data types

### 10.3 CDC Testing
- Simulate INSERT, UPDATE, DELETE operations
- Test with high-frequency changes
- Verify timestamp accuracy
- Monitor replication lag

---

## 11. Success Criteria

The Django backend is complete when:

1. ✅ All models are implemented with proper relationships
2. ✅ Docker environment runs successfully
3. ✅ Seed commands generate realistic data at scale
4. ✅ Multi-tenant isolation is enforced
5. ✅ Activity simulation creates CDC events
6. ✅ Data supports all target metrics
7. ✅ PostgreSQL is configured for DMS replication
8. ✅ Documentation is complete
9. ✅ Sample queries demonstrate value
10. ✅ Performance is acceptable (seed 100K records < 5 min)

---

## 12. Next Steps After Django Backend

Once the backend is complete:

1. **Export sample data** for testing
2. **Document database schema** for DMS mapping
3. **Create sample Athena queries** to validate in Gold layer
4. **Begin Terraform infrastructure** (Step 2)
5. **Set up DMS replication task**
6. **Implement Glue transformations**
7. **Configure Lake Formation policies**

---

## Estimated Timeline

- **Total Duration**: 4-5 days
- **Core Development**: 3 days
- **Testing & Refinement**: 1 day
- **Documentation**: 1 day

---

## Notes

- Keep the implementation simple and focused on the POC goals
- Prioritize data quality over feature completeness
- Ensure data is realistic enough to demonstrate business value
- Make it easy to scale up/down for different demo scenarios
- Document everything for the residency presentation
