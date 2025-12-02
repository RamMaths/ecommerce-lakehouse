# Terraform Infrastructure Plan
## Lakehouse POC - AWS Data Architecture

---

## 1. Project Overview

**Purpose**: Provision AWS infrastructure to replicate PostgreSQL data from Django backend to S3, transform it through medallion architecture (Bronze/Silver/Gold), and enable analytics via Athena.

**Architecture Pattern**: Lakehouse with CDC replication, Apache Hudi for ACID transactions, and Lake Formation for governance.

**Correlation with Django Backend**: 
- Django models → DMS source tables
- Multi-tenant data → Lake Formation row-level security
- Historical data → Time-travel queries with Hudi
- Metrics requirements → Athena query patterns

---

## 2. High-Level Architecture

```
┌─────────────────┐
│ Django Backend  │
│  (PostgreSQL)   │
└────────┬────────┘
         │
         │ AWS DMS (CDC)
         ↓
┌─────────────────────────────────────────────────────────┐
│                    Amazon S3                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│  │  Bronze  │ → │  Silver  │ → │   Gold   │           │
│  │   Raw    │   │  Cleaned │   │ Optimized│           │
│  │ Parquet  │   │   Hudi   │   │   Hudi   │           │
│  └──────────┘   └──────────┘   └──────────┘           │
└─────────────────────────────────────────────────────────┘
         │                │                │
         ↓                ↓                ↓
    ┌────────────────────────────────────────┐
    │      AWS Glue Data Catalog             │
    │  (Metadata, Schema, Partitions)        │
    └────────────────────────────────────────┘
         │                │                │
         ↓                ↓                ↓
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │  Glue   │    │  Athena  │    │   Lake   │
    │  Jobs   │    │ Queries  │    │Formation │
    └─────────┘    └──────────┘    └──────────┘
```

---

## 3. AWS Services & Components

### 3.1 Data Ingestion Layer

**AWS DMS (Database Migration Service)**
- **Replication Instance**: t3.medium (adjustable based on load)
- **Source Endpoint**: PostgreSQL (Django backend)
- **Target Endpoint**: S3 (Bronze layer)
- **Replication Task**: Full load + CDC (ongoing replication)
- **Table Mappings**: All 8 Django models (Tenant, Customer, Product, Order, OrderItem, Event, Subscription, Invoice)

**Configuration**:
- CDC enabled for real-time changes
- Parquet format for S3 output
- Partitioning by `load_date` and `tenant_id`
- Compression: Snappy
- Batch size: 10,000 records

### 3.2 Storage Layer

**Amazon S3 Buckets**

1. **Bronze Bucket** (`lakehouse-poc-bronze-{account-id}`)
   - **Purpose**: Raw data from DMS
   - **Format**: Parquet
   - **Partitioning**: `s3://bucket/table_name/load_date=YYYY-MM-DD/tenant_id=xxx/`
   - **Lifecycle**: Transition to IA after 90 days, Glacier after 180 days
   - **Versioning**: Enabled
   - **Encryption**: SSE-S3

2. **Silver Bucket** (`lakehouse-poc-silver-{account-id}`)
   - **Purpose**: Cleaned, standardized data
   - **Format**: Apache Hudi (Copy-on-Write)
   - **Partitioning**: `tenant_id`, `load_date`
   - **Features**: Schema evolution, upserts, time-travel
   - **Lifecycle**: Transition to IA after 180 days
   - **Encryption**: SSE-S3

3. **Gold Bucket** (`lakehouse-poc-gold-{account-id}`)
   - **Purpose**: Business-ready aggregated tables
   - **Format**: Apache Hudi (Merge-on-Read for analytics)
   - **Partitioning**: `dt` (event date), `tenant_id`
   - **Tables**: Pre-aggregated metrics, dimensional models
   - **Lifecycle**: Keep hot for 365 days
   - **Encryption**: SSE-S3

4. **Scripts Bucket** (`lakehouse-poc-scripts-{account-id}`)
   - **Purpose**: Glue job scripts, SQL queries, utilities
   - **Versioning**: Enabled

5. **Athena Results Bucket** (`lakehouse-poc-athena-results-{account-id}`)
   - **Purpose**: Query results storage
   - **Lifecycle**: Delete after 30 days

### 3.3 Processing Layer

**AWS Glue**

1. **Glue Crawlers**
   - `bronze-crawler`: Discovers raw tables from DMS
   - `silver-crawler`: Catalogs Hudi tables in Silver
   - `gold-crawler`: Catalogs aggregated tables in Gold
   - **Schedule**: Hourly for Bronze, Daily for Silver/Gold

2. **Glue ETL Jobs**

   **Bronze → Silver Jobs**:
   - `bronze_to_silver_customers`: Clean customer data, deduplicate, standardize
   - `bronze_to_silver_products`: Validate products, enrich categories
   - `bronze_to_silver_orders`: Calculate totals, validate statuses
   - `bronze_to_silver_events`: Parse JSON, sessionize, enrich
   - `bronze_to_silver_subscriptions`: Calculate MRR, status transitions
   - `bronze_to_silver_invoices`: Payment reconciliation
   
   **Silver → Gold Jobs**:
   - `silver_to_gold_revenue_metrics`: Daily/monthly revenue by tenant
   - `silver_to_gold_customer_metrics`: LTV, retention, churn
   - `silver_to_gold_product_metrics`: Sales performance, inventory
   - `silver_to_gold_funnel_metrics`: Conversion analysis
   - `silver_to_gold_subscription_metrics`: MRR, ARR, churn rate

3. **Glue Data Catalog**
   - **Databases**: 
     - `lakehouse_bronze`: Raw tables
     - `lakehouse_silver`: Cleaned tables
     - `lakehouse_gold`: Aggregated tables
   - **Tables**: Auto-discovered by crawlers + manually defined Hudi tables
   - **Partitions**: Managed automatically

4. **Glue Job Configuration**
   - **Worker Type**: G.1X (4 vCPU, 16 GB memory)
   - **Number of Workers**: 2-5 (auto-scaling)
   - **Timeout**: 60 minutes
   - **Max Retries**: 1
   - **Glue Version**: 4.0 (supports Hudi 0.12+)

### 3.4 Query Layer

**Amazon Athena**

1. **Workgroups**
   - `primary`: Default workgroup
   - `analytics-team`: For BI analysts
   - `data-engineering`: For data engineers
   - **Configuration**: 
     - Query result location: Athena results bucket
     - Encryption: Enabled
     - Bytes scanned per query limit: 1 TB

2. **Prepared Queries** (Saved Queries)
   - Revenue by tenant over time
   - Customer acquisition trends
   - Product performance dashboard
   - Subscription MRR tracking
   - Event funnel analysis

3. **Query Optimization**
   - Partition pruning on `tenant_id` and date columns
   - Columnar format (Parquet/Hudi)
   - Compression (Snappy)
   - Statistics collection via Glue

### 3.5 Governance Layer

**AWS Lake Formation**

1. **Data Lake Location**: Register S3 buckets (Bronze, Silver, Gold)

2. **Permissions Model**
   - **Database-level**: Grant access to specific databases
   - **Table-level**: Grant SELECT on specific tables
   - **Column-level**: Restrict PII columns (email, phone)
   - **Row-level**: Filter by `tenant_id` for multi-tenant isolation

3. **Data Filters** (Row-Level Security)
   - `tenant_filter_enterprise`: WHERE tenant_id IN ('tenant-1', 'tenant-2')
   - `tenant_filter_midmarket`: WHERE tenant_id IN ('tenant-3', 'tenant-4', 'tenant-5')
   - `tenant_filter_small`: WHERE tenant_id IN ('tenant-6', 'tenant-7', 'tenant-8')

4. **IAM Roles & Principals**
   - `LakeFormationAdmin`: Full access
   - `DataEngineer`: Read/Write Silver/Gold, Read Bronze
   - `DataAnalyst`: Read Gold only
   - `TenantSpecificAnalyst`: Read Gold with row-level filter

### 3.6 Monitoring & Logging

**CloudWatch**
- DMS task monitoring (latency, CDC lag)
- Glue job execution logs
- Athena query metrics
- S3 bucket metrics

**CloudTrail**
- API call auditing
- Data access logs
- Compliance tracking

**SNS Topics**
- DMS failure alerts
- Glue job failure notifications
- Cost anomaly alerts

---

## 4. Terraform Project Structure

```
terraform-infra/
├── README.md
├── .gitignore
├── terraform.tfvars.example
├── versions.tf                  # Terraform & provider versions
├── variables.tf                 # Global variables
├── outputs.tf                   # Stack outputs
├── main.tf                      # Root module orchestration
├── backend.tf                   # S3 backend for state
│
├── modules/
│   ├── networking/              # VPC, Subnets, Security Groups
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── dms/                     # DMS replication
│   │   ├── main.tf
│   │   ├── replication_instance.tf
│   │   ├── endpoints.tf
│   │   ├── replication_tasks.tf
│   │   ├── table_mappings.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── s3/                      # S3 buckets & policies
│   │   ├── main.tf
│   │   ├── bronze_bucket.tf
│   │   ├── silver_bucket.tf
│   │   ├── gold_bucket.tf
│   │   ├── scripts_bucket.tf
│   │   ├── athena_bucket.tf
│   │   ├── lifecycle_policies.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── glue/                    # Glue resources
│   │   ├── main.tf
│   │   ├── databases.tf
│   │   ├── crawlers.tf
│   │   ├── jobs_bronze_to_silver.tf
│   │   ├── jobs_silver_to_gold.tf
│   │   ├── triggers.tf
│   │   ├── iam.tf
│   │   ├── scripts/             # PySpark job scripts
│   │   │   ├── bronze_to_silver_customers.py
│   │   │   ├── bronze_to_silver_orders.py
│   │   │   ├── silver_to_gold_revenue.py
│   │   │   └── ...
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── athena/                  # Athena workgroups & queries
│   │   ├── main.tf
│   │   ├── workgroups.tf
│   │   ├── named_queries.tf
│   │   ├── queries/             # SQL query files
│   │   │   ├── revenue_by_tenant.sql
│   │   │   ├── customer_ltv.sql
│   │   │   └── ...
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── lake-formation/          # Lake Formation governance
│   │   ├── main.tf
│   │   ├── data_lake_settings.tf
│   │   ├── permissions.tf
│   │   ├── data_filters.tf
│   │   ├── iam_roles.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── monitoring/              # CloudWatch, SNS
│   │   ├── main.tf
│   │   ├── cloudwatch_alarms.tf
│   │   ├── sns_topics.tf
│   │   ├── dashboards.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── iam/                     # IAM roles & policies
│       ├── main.tf
│       ├── dms_roles.tf
│       ├── glue_roles.tf
│       ├── athena_roles.tf
│       ├── lake_formation_roles.tf
│       ├── policies.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   ├── backend.tf
│   │   └── outputs.tf
│   │
│   └── prod/
│       ├── main.tf
│       ├── terraform.tfvars
│       ├── backend.tf
│       └── outputs.tf
│
└── docs/
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    ├── COST_ESTIMATION.md
    └── TROUBLESHOOTING.md
```

---

## 5. Django Backend → AWS Mapping

### 5.1 Table Mapping (DMS Configuration)

| Django Model | DMS Source Table | Bronze S3 Path | Silver Hudi Table | Gold Aggregations |
|--------------|------------------|----------------|-------------------|-------------------|
| Tenant | core_tenant | bronze/tenant/ | silver.tenant | gold.tenant_summary |
| Customer | core_customer | bronze/customer/ | silver.customer | gold.customer_metrics |
| Product | core_product | bronze/product/ | silver.product | gold.product_performance |
| Order | core_order | bronze/order/ | silver.order | gold.revenue_metrics |
| OrderItem | core_orderitem | bronze/orderitem/ | silver.orderitem | gold.product_sales |
| Event | core_event | bronze/event/ | silver.event | gold.funnel_metrics |
| Subscription | core_subscription | bronze/subscription/ | silver.subscription | gold.mrr_metrics |
| Invoice | core_invoice | bronze/invoice/ | silver.invoice | gold.payment_metrics |

### 5.2 Partitioning Strategy

**Bronze Layer** (from DMS):
```
s3://lakehouse-poc-bronze/core_order/
  load_date=2025-01-15/
    tenant_id=tenant-1/
      data.parquet
    tenant_id=tenant-2/
      data.parquet
```

**Silver Layer** (Hudi):
```
s3://lakehouse-poc-silver/order/
  tenant_id=tenant-1/
    load_date=2025-01-15/
      .hoodie/
      <hudi_files>.parquet
```

**Gold Layer** (Hudi):
```
s3://lakehouse-poc-gold/revenue_metrics/
  dt=2025-01-15/
    tenant_id=tenant-1/
      <hudi_files>.parquet
```

### 5.3 Data Transformations

**Bronze → Silver Transformations**:

1. **Customers**:
   - Deduplicate by email + tenant_id
   - Standardize phone numbers
   - Parse metadata JSON
   - Add data quality flags

2. **Orders**:
   - Recalculate totals (subtotal + tax + shipping)
   - Validate status transitions
   - Enrich with customer/product dimensions
   - Handle late-arriving data

3. **Events**:
   - Parse event_data JSON
   - Sessionize (group by session_id)
   - Calculate session metrics
   - Anonymize IP addresses

4. **Subscriptions**:
   - Calculate MRR from monthly_amount
   - Track status changes over time
   - Identify churn events

**Silver → Gold Transformations**:

1. **Revenue Metrics** (Daily aggregation):
   ```sql
   SELECT 
     tenant_id,
     DATE(order_date) as dt,
     COUNT(DISTINCT order_id) as order_count,
     COUNT(DISTINCT customer_id) as unique_customers,
     SUM(total) as total_revenue,
     AVG(total) as avg_order_value
   FROM silver.order
   WHERE status = 'completed'
   GROUP BY tenant_id, DATE(order_date)
   ```

2. **Customer Metrics** (Daily snapshot):
   ```sql
   SELECT
     tenant_id,
     CURRENT_DATE as dt,
     COUNT(*) as total_customers,
     COUNT(CASE WHEN created_at >= CURRENT_DATE - 30 THEN 1 END) as new_customers_30d,
     -- LTV calculation
     -- Retention cohorts
   FROM silver.customer
   GROUP BY tenant_id
   ```

3. **Funnel Metrics** (Hourly):
   ```sql
   SELECT
     tenant_id,
     DATE_TRUNC('hour', created_at) as dt,
     COUNT(CASE WHEN event_type = 'page_view' THEN 1 END) as page_views,
     COUNT(CASE WHEN event_type = 'product_view' THEN 1 END) as product_views,
     COUNT(CASE WHEN event_type = 'add_to_cart' THEN 1 END) as add_to_cart,
     COUNT(CASE WHEN event_type = 'checkout' THEN 1 END) as checkouts
   FROM silver.event
   GROUP BY tenant_id, DATE_TRUNC('hour', created_at)
   ```

---

## 6. Implementation Phases

### Phase 1: Foundation (Day 1)
- [ ] Set up Terraform project structure
- [ ] Configure AWS provider and backend
- [ ] Create IAM module with base roles
- [ ] Set up networking module (VPC, subnets, security groups)
- [ ] Initialize S3 module with all buckets
- [ ] Configure lifecycle policies

### Phase 2: Data Ingestion (Day 2)
- [ ] Implement DMS module
- [ ] Create replication instance
- [ ] Configure source endpoint (PostgreSQL)
- [ ] Configure target endpoint (S3 Bronze)
- [ ] Define table mappings for all 8 Django models
- [ ] Create replication task (full load + CDC)
- [ ] Test connectivity and initial load

### Phase 3: Data Catalog (Day 2-3)
- [ ] Implement Glue module
- [ ] Create Glue databases (bronze, silver, gold)
- [ ] Configure Bronze crawler
- [ ] Set up crawler schedules
- [ ] Test catalog discovery

### Phase 4: Bronze → Silver Pipeline (Day 3-4)
- [ ] Write PySpark scripts for each table transformation
- [ ] Implement Hudi write operations
- [ ] Create Glue jobs for Bronze → Silver
- [ ] Configure job triggers
- [ ] Test transformations with sample data
- [ ] Set up Silver crawler

### Phase 5: Silver → Gold Pipeline (Day 4-5)
- [ ] Design Gold layer schema (star schema)
- [ ] Write aggregation PySpark scripts
- [ ] Create Glue jobs for Silver → Gold
- [ ] Implement incremental processing
- [ ] Configure job dependencies
- [ ] Set up Gold crawler

### Phase 6: Query Layer (Day 5)
- [ ] Implement Athena module
- [ ] Create workgroups
- [ ] Write named queries for key metrics
- [ ] Test query performance
- [ ] Optimize partitioning

### Phase 7: Governance (Day 6)
- [ ] Implement Lake Formation module
- [ ] Register data lake locations
- [ ] Create IAM roles for different personas
- [ ] Configure database/table permissions
- [ ] Set up row-level security filters
- [ ] Test multi-tenant isolation

### Phase 8: Monitoring (Day 6)
- [ ] Implement monitoring module
- [ ] Create CloudWatch dashboards
- [ ] Set up alarms for DMS, Glue, Athena
- [ ] Configure SNS notifications
- [ ] Enable CloudTrail logging

### Phase 9: Testing & Validation (Day 7)
- [ ] End-to-end testing with Django data
- [ ] Validate CDC replication
- [ ] Test all Glue jobs
- [ ] Run sample Athena queries
- [ ] Verify Lake Formation permissions
- [ ] Performance testing
- [ ] Cost analysis

### Phase 10: Documentation (Day 7-8)
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Cost estimation document
- [ ] Troubleshooting guide
- [ ] Sample queries and dashboards
- [ ] Presentation materials

---

## 7. Key Variables & Configuration

### 7.1 Global Variables

```hcl
variable "project_name" {
  default = "lakehouse-poc"
}

variable "environment" {
  description = "dev or prod"
}

variable "aws_region" {
  default = "us-east-1"
}

variable "tags" {
  type = map(string)
  default = {
    Project     = "Lakehouse POC"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}
```

### 7.2 DMS Variables

```hcl
variable "source_db_host" {
  description = "Django PostgreSQL host"
}

variable "source_db_port" {
  default = 5432
}

variable "source_db_name" {
  default = "lakehouse_poc"
}

variable "source_db_username" {
  sensitive = true
}

variable "source_db_password" {
  sensitive = true
}

variable "dms_instance_class" {
  default = "dms.t3.medium"
}

variable "dms_allocated_storage" {
  default = 100 # GB
}
```

### 7.3 Glue Variables

```hcl
variable "glue_worker_type" {
  default = "G.1X"
}

variable "glue_number_of_workers" {
  default = 2
}

variable "glue_version" {
  default = "4.0"
}
```

---

## 8. Cost Estimation

### 8.1 Monthly Cost Breakdown (Dev Environment)

| Service | Resource | Estimated Cost |
|---------|----------|----------------|
| **DMS** | t3.medium replication instance (24/7) | $70 |
| **S3** | 100 GB storage (Bronze/Silver/Gold) | $2.30 |
| **S3** | Data transfer & requests | $5 |
| **Glue** | Crawlers (hourly, 3 crawlers) | $13 |
| **Glue** | ETL Jobs (10 jobs, 2 DPU, 30 min/day) | $33 |
| **Athena** | 100 GB scanned per month | $0.50 |
| **Lake Formation** | No additional cost | $0 |
| **CloudWatch** | Logs & metrics | $10 |
| **VPC** | NAT Gateway (if needed) | $32 |
| **Total** | | **~$165/month** |

### 8.2 Cost Optimization Strategies

1. **DMS**: Stop replication instance when not actively testing
2. **Glue**: Use job bookmarks to avoid reprocessing
3. **S3**: Implement lifecycle policies aggressively
4. **Athena**: Use partitioning and columnar formats
5. **Development**: Use smaller instance types, scale up for prod

---

## 9. Non-Functional Requirements Testing

### 9.1 Performance Metrics

**DMS Replication**:
- Initial full load time: < 30 minutes for 100K records
- CDC latency: < 5 seconds
- Throughput: > 10,000 records/minute

**Glue Jobs**:
- Bronze → Silver: < 10 minutes for daily batch
- Silver → Gold: < 5 minutes for aggregations
- Job startup time: < 2 minutes

**Athena Queries**:
- Simple aggregation (1 month, 1 tenant): < 3 seconds
- Complex join (6 months, all tenants): < 15 seconds
- Full table scan: < 30 seconds

### 9.2 Reliability Metrics

- DMS uptime: 99.9%
- Glue job success rate: > 95%
- Data freshness: < 10 minutes from source to Silver
- Data quality: > 99% valid records

### 9.3 Scalability Testing

- Test with 1M records
- Test with 20 tenants
- Test with 1 year of historical data
- Concurrent Athena queries: 10+

---

## 10. Security Considerations

### 10.1 Data Encryption

- **At Rest**: S3 SSE-S3 encryption
- **In Transit**: TLS for all connections
- **DMS**: Encrypted replication instance storage

### 10.2 Access Control

- **IAM**: Least privilege principle
- **Lake Formation**: Row/column-level security
- **S3**: Bucket policies + IAM policies
- **Secrets Manager**: Store database credentials

### 10.3 Network Security

- **VPC**: Private subnets for DMS
- **Security Groups**: Restrict PostgreSQL access
- **VPC Endpoints**: S3, Glue (avoid NAT costs)

### 10.4 Audit & Compliance

- **CloudTrail**: All API calls logged
- **S3 Access Logs**: Track data access
- **Glue Job Logs**: Transformation audit trail

---

## 11. Integration with Django Backend

### 11.1 Prerequisites

Before running Terraform:
1. Django backend is running and accessible
2. PostgreSQL has logical replication enabled
3. Database user has replication permissions
4. Network connectivity from AWS to Django host
5. Sample data is seeded (at least 10K records)

### 11.2 Connection Setup

**Option A: Public Internet** (for POC)
- Django PostgreSQL exposed with public IP
- Security group allows AWS DMS IP ranges
- SSL/TLS connection required

**Option B: VPN/Direct Connect** (for production)
- Site-to-site VPN between AWS and Django host
- Private IP connectivity
- More secure, higher cost

**Option C: AWS-hosted Django** (recommended for POC)
- Deploy Django to EC2 or ECS in same VPC
- Private connectivity to DMS
- Simplest setup

### 11.3 DMS Table Mappings

Terraform will generate table mappings from Django models:

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all-tables",
      "object-locator": {
        "schema-name": "public",
        "table-name": "core_%"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "transformation",
      "rule-id": "2",
      "rule-name": "add-tenant-partition",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "public",
        "table-name": "%"
      },
      "rule-action": "add-column",
      "value": "tenant_id",
      "expression": "$tenant_id",
      "data-type": {
        "type": "string"
      }
    }
  ]
}
```

---

## 12. Success Criteria

The Terraform infrastructure is complete when:

1. ✅ All modules are implemented and tested
2. ✅ DMS successfully replicates Django data to S3
3. ✅ Bronze crawler discovers all tables
4. ✅ Glue jobs transform data to Silver layer
5. ✅ Hudi tables support upserts and time-travel
6. ✅ Gold layer contains aggregated metrics
7. ✅ Athena queries return correct results
8. ✅ Lake Formation enforces multi-tenant isolation
9. ✅ Monitoring dashboards show system health
10. ✅ Cost is within budget ($200/month for dev)
11. ✅ Documentation is complete
12. ✅ End-to-end demo works reliably

---

## 13. Demo Scenarios

### Scenario 1: Real-time CDC
1. Insert new order in Django
2. Show DMS replication (< 5 seconds)
3. Run Glue job to update Silver
4. Query in Athena to see new data

### Scenario 2: Historical Analysis
1. Query revenue trends over 6 months
2. Show partition pruning performance
3. Compare query times: Bronze vs Silver vs Gold

### Scenario 3: Multi-tenant Isolation
1. Login as Tenant A analyst
2. Query Gold layer - see only Tenant A data
3. Login as Tenant B analyst
4. Verify data isolation

### Scenario 4: Time Travel
1. Show current state of customer table
2. Query Hudi table as of 1 week ago
3. Demonstrate data recovery capability

### Scenario 5: Cost Optimization
1. Show S3 storage costs by layer
2. Demonstrate lifecycle policies
3. Compare Athena query costs with/without partitioning

---

## 14. Next Steps After Terraform

1. **Build BI Dashboards**: Connect Tableau/QuickSight to Athena
2. **Implement Data Quality**: Great Expectations or Deequ
3. **Add ML Pipeline**: SageMaker for predictive analytics
4. **Automate Testing**: Terraform tests, data validation
5. **Production Hardening**: Multi-region, disaster recovery
6. **Documentation**: Runbooks, architecture decision records

---

## Estimated Timeline

- **Total Duration**: 7-8 days
- **Core Infrastructure**: 4 days
- **Data Pipelines**: 2 days
- **Testing & Optimization**: 1-2 days
- **Documentation**: 1 day

---

## Notes

- Start with minimal viable infrastructure, iterate
- Test each module independently before integration
- Use Terraform workspaces for dev/prod separation
- Keep costs low by stopping resources when not in use
- Document all design decisions for residency presentation
- Focus on demonstrating value, not perfection
