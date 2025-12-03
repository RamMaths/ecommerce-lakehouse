# Terraform Deployment Guide

Step-by-step guide to deploy the lakehouse infrastructure.

## Pre-Deployment Checklist

- [ ] Django backend is running with data seeded
- [ ] PostgreSQL publication created (`dms_publication`)
- [ ] AWS CLI configured with profile "ramses"
- [ ] Terraform installed (v1.5+)
- [ ] Decision made on network connectivity (ngrok/EC2/RDS)

## Step 1: Prepare Django PostgreSQL for AWS Access

### Option A: Using ngrok (Quick Testing)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start ngrok tunnel to PostgreSQL
ngrok tcp 5432

# Note the forwarding address (e.g., 0.tcp.ngrok.io:12345)
# You'll use this as source_db_host
```

### Option B: Deploy Django to EC2 (Recommended)

See separate EC2 deployment guide (to be created).

### Option C: Use Existing RDS

If you have an RDS instance, use its endpoint directly.

## Step 2: Configure Terraform Variables

```bash
cd terraform-infra

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

**Update these values:**

```hcl
# Your Django PostgreSQL connection
source_db_host     = "your-ngrok-url.ngrok.io"  # or EC2 IP or RDS endpoint
source_db_port     = 12345                       # ngrok port or 5432
source_db_password = "secure_password"           # your actual password

# AWS configuration
aws_profile = "ramses"
aws_region  = "us-east-1"
owner       = "your-name"
```

## Step 3: Initialize Terraform

```bash
# Initialize Terraform (downloads providers)
terraform init

# Expected output:
# Terraform has been successfully initialized!
```

## Step 4: Review Deployment Plan

```bash
# Generate and review execution plan
terraform plan

# Review the output carefully
# Should show ~30-40 resources to be created
```

**Key resources to verify:**
- 5 S3 buckets (bronze, silver, gold, scripts, athena)
- 1 DMS replication instance
- 2 DMS endpoints
- 1 DMS replication task
- 3 Glue databases
- 3 Glue crawlers
- 1 Athena workgroup
- 5 Athena named queries
- Multiple IAM roles

## Step 5: Deploy Infrastructure

```bash
# Apply configuration
terraform apply

# Review the plan again
# Type 'yes' to confirm

# Wait 10-15 minutes for deployment
# (DMS instance creation is slow)
```

**Monitor progress:**
- Watch the terminal output
- Check AWS Console (DMS, S3, Glue)

## Step 6: Verify Deployment

```bash
# Check Terraform outputs
terraform output

# Verify S3 buckets were created
aws s3 ls --profile ramses | grep lakehouse-poc

# Check DMS instance status
aws dms describe-replication-instances \
  --profile ramses \
  --query 'ReplicationInstances[0].ReplicationInstanceStatus'

# Should return: "available"
```

## Step 7: Test DMS Source Connection

```bash
# Get endpoint ARN from outputs
SOURCE_ENDPOINT=$(terraform output -raw dms_replication_instance_endpoint)

# Test connection to Django PostgreSQL
aws dms test-connection \
  --replication-instance-arn $(terraform output -raw dms_replication_instance_endpoint) \
  --endpoint-arn $(terraform output -json | jq -r '.source_endpoint_arn.value') \
  --profile ramses

# Wait 2-3 minutes, then check status
aws dms describe-connections \
  --profile ramses \
  --filters Name=endpoint-arn,Values=$(terraform output -json | jq -r '.source_endpoint_arn.value')

# Status should be: "successful"
```

**If connection fails:**
- Check ngrok is still running
- Verify PostgreSQL is accessible
- Check security groups
- Review DMS logs in AWS Console

## Step 8: Start DMS Replication

```bash
# Get replication task ARN
TASK_ARN=$(terraform output -json | jq -r '.dms_replication_task_arn.value')

# Start replication (full load + CDC)
aws dms start-replication-task \
  --replication-task-arn $TASK_ARN \
  --start-replication-task-type start-replication \
  --profile ramses

# Monitor progress
watch -n 10 'aws dms describe-replication-tasks \
  --filters Name=replication-task-arn,Values='$TASK_ARN' \
  --profile ramses \
  --query "ReplicationTasks[0].[Status,ReplicationTaskStats]"'

# Wait for status: "running" or "load complete"
```

**Expected timeline:**
- Initial load: 5-10 minutes (for medium scale data)
- CDC: Continuous after initial load

## Step 9: Verify Data in S3

```bash
# Get Bronze bucket name
BRONZE_BUCKET=$(terraform output -json | jq -r '.s3_buckets.value.bronze')

# List replicated data
aws s3 ls s3://$BRONZE_BUCKET/dms-data/ --recursive --profile ramses

# You should see Parquet files for each table:
# - core_tenant/
# - core_customer/
# - core_product/
# - core_order/
# - core_orderitem/
# - core_event/
# - core_subscription/
# - core_invoice/
```

## Step 10: Run Glue Crawler

```bash
# Start Bronze crawler to discover tables
aws glue start-crawler \
  --name lakehouse-poc-dev-bronze-crawler \
  --profile ramses

# Check crawler status
watch -n 10 'aws glue get-crawler \
  --name lakehouse-poc-dev-bronze-crawler \
  --profile ramses \
  --query "Crawler.State"'

# Wait for status: "READY" (takes 2-5 minutes)
```

## Step 11: Verify Glue Catalog

```bash
# List tables in Bronze database
aws glue get-tables \
  --database-name lakehouse_poc_dev_bronze \
  --profile ramses \
  --query 'TableList[*].Name'

# Should show all 8 core tables
```

## Step 12: Query Data in Athena

### Using AWS Console

1. Open Athena Console
2. Select workgroup: `lakehouse-poc-dev-workgroup`
3. Select database: `lakehouse_poc_dev_bronze`
4. Run query:

```sql
SELECT COUNT(*) as tenant_count FROM core_tenant;
```

### Using AWS CLI

```bash
# Get Athena bucket
ATHENA_BUCKET=$(terraform output -json | jq -r '.s3_buckets.value.athena')

# Run query
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM core_tenant" \
  --query-execution-context Database=lakehouse_poc_dev_bronze \
  --result-configuration OutputLocation=s3://$ATHENA_BUCKET/query-results/ \
  --work-group lakehouse-poc-dev-workgroup \
  --profile ramses \
  --query 'QueryExecutionId' \
  --output text)

# Wait for query to complete
aws athena get-query-execution \
  --query-execution-id $QUERY_ID \
  --profile ramses \
  --query 'QueryExecution.Status.State'

# Get results
aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --profile ramses
```

## Step 13: Run Named Queries

```bash
# List available named queries
aws athena list-named-queries \
  --work-group lakehouse-poc-dev-workgroup \
  --profile ramses

# Run revenue by tenant query
aws athena start-query-execution \
  --named-query-id <query-id-from-output> \
  --profile ramses
```

## Verification Checklist

After deployment, verify:

- [ ] All S3 buckets created
- [ ] DMS instance is "available"
- [ ] DMS source endpoint connection successful
- [ ] DMS replication task is "running"
- [ ] Data visible in Bronze S3 bucket
- [ ] Glue crawler completed successfully
- [ ] Tables visible in Glue Data Catalog
- [ ] Athena queries return data
- [ ] Named queries work correctly

## Troubleshooting

### Issue: DMS connection test fails

**Solution:**
```bash
# Check PostgreSQL is accessible
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SELECT 1;"

# Check ngrok is running
curl http://localhost:4040/api/tunnels

# Verify credentials in terraform.tfvars
```

### Issue: No data in S3 after replication

**Solution:**
```bash
# Check DMS task status
aws dms describe-replication-tasks --profile ramses

# Check DMS task logs in CloudWatch
# AWS Console → CloudWatch → Log Groups → dms-tasks-*

# Verify table mappings include your tables
```

### Issue: Glue crawler finds no tables

**Solution:**
```bash
# Verify data exists in S3
aws s3 ls s3://$BRONZE_BUCKET/dms-data/ --recursive --profile ramses

# Check crawler configuration
aws glue get-crawler --name lakehouse-poc-dev-bronze-crawler --profile ramses

# Run crawler again
aws glue start-crawler --name lakehouse-poc-dev-bronze-crawler --profile ramses
```

### Issue: Athena query fails

**Solution:**
```bash
# Verify database exists
aws glue get-database --name lakehouse_poc_dev_bronze --profile ramses

# Check table schema
aws glue get-table \
  --database-name lakehouse_poc_dev_bronze \
  --name core_tenant \
  --profile ramses

# Try simpler query first
# SELECT * FROM core_tenant LIMIT 10;
```

## Cost Monitoring

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-12-01,End=2024-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --profile ramses

# Set up billing alert (recommended)
# AWS Console → Billing → Budgets → Create budget
```

## Next Steps

After successful deployment:

1. ✅ Test CDC by updating records in Django
2. ✅ Verify changes appear in S3
3. ⏳ Create Glue ETL jobs for Silver layer
4. ⏳ Implement Gold layer aggregations
5. ⏳ Set up Lake Formation governance
6. ⏳ Create BI dashboards with QuickSight

## Cleanup

When done testing:

```bash
# Stop DMS task
aws dms stop-replication-task \
  --replication-task-arn $TASK_ARN \
  --profile ramses

# Wait for task to stop
# Then destroy infrastructure
terraform destroy

# Type 'yes' to confirm
```

**Note:** Empty S3 buckets first if they have data:

```bash
aws s3 rm s3://$BRONZE_BUCKET --recursive --profile ramses
aws s3 rm s3://$SILVER_BUCKET --recursive --profile ramses
aws s3 rm s3://$GOLD_BUCKET --recursive --profile ramses
```

## Success Criteria

Deployment is successful when:

✅ All Terraform resources created without errors
✅ DMS replication task shows "running" status
✅ Data visible in Bronze S3 bucket (Parquet files)
✅ Glue crawler discovers all 8 tables
✅ Athena queries return correct data
✅ Named queries execute successfully
✅ No errors in CloudWatch logs

---

**Estimated Time:** 30-45 minutes (including DMS instance creation)

**Cost:** ~$90/month (can be reduced by stopping DMS when not in use)
