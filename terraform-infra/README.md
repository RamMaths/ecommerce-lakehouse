# Terraform Infrastructure - Lakehouse POC

AWS infrastructure for the lakehouse POC using Terraform.

## Architecture

This Terraform configuration deploys:

- **S3 Buckets**: Bronze, Silver, Gold layers + Scripts + Athena results
- **AWS DMS**: Replication instance, endpoints, and tasks for PostgreSQL → S3
- **AWS Glue**: Data Catalog databases and crawlers for each layer
- **Amazon Athena**: Workgroup and named queries for analytics
- **IAM**: Roles and policies for all services

## Prerequisites

1. **AWS CLI configured** with profile "ramses"
   ```bash
   aws configure --profile ramses
   ```

2. **Terraform installed** (v1.5+)
   ```bash
   terraform version
   ```

3. **Django backend running** with data seeded
   - PostgreSQL must be accessible from AWS
   - Publication created for DMS

4. **Network access** from AWS to Django PostgreSQL
   - Option A: Use ngrok or similar for local testing
   - Option B: Deploy Django to EC2 (recommended)
   - Option C: Use RDS as source

## Quick Start

### 1. Configure Variables

```bash
# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required variables:**
- `source_db_host`: Your Django PostgreSQL host (IP or hostname)
- `source_db_password`: Your PostgreSQL password

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan Deployment

```bash
terraform plan
```

Review the resources that will be created:
- 5 S3 buckets
- 1 DMS replication instance
- 2 DMS endpoints (source + target)
- 1 DMS replication task
- 3 Glue databases
- 3 Glue crawlers
- 1 Athena workgroup
- 5 Athena named queries
- Multiple IAM roles and policies

### 4. Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. Deployment takes ~10-15 minutes (DMS instance creation is slow).

### 5. Verify Deployment

```bash
# Check outputs
terraform output

# List S3 buckets
aws s3 ls --profile ramses | grep lakehouse-poc

# Check DMS instance status
aws dms describe-replication-instances --profile ramses
```

## Post-Deployment Steps

### 1. Test DMS Source Endpoint

```bash
# Get endpoint ARN from outputs
terraform output

# Test connection
aws dms test-connection \
  --replication-instance-arn <replication-instance-arn> \
  --endpoint-arn <source-endpoint-arn> \
  --profile ramses
```

### 2. Start DMS Replication Task

```bash
# Start the replication task
aws dms start-replication-task \
  --replication-task-arn <task-arn> \
  --start-replication-task-type start-replication \
  --profile ramses

# Monitor progress
aws dms describe-replication-tasks \
  --filters Name=replication-task-arn,Values=<task-arn> \
  --profile ramses
```

### 3. Run Glue Crawlers

```bash
# Start Bronze crawler (after DMS has replicated data)
aws glue start-crawler \
  --name lakehouse-poc-dev-bronze-crawler \
  --profile ramses

# Check crawler status
aws glue get-crawler \
  --name lakehouse-poc-dev-bronze-crawler \
  --profile ramses
```

### 4. Query Data in Athena

```bash
# Open Athena console
# Or use AWS CLI
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM lakehouse_poc_dev_bronze.core_tenant" \
  --query-execution-context Database=lakehouse_poc_dev_bronze \
  --result-configuration OutputLocation=s3://<athena-bucket>/query-results/ \
  --work-group lakehouse-poc-dev-workgroup \
  --profile ramses
```

## Module Structure

```
terraform-infra/
├── main.tf                 # Root module
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── versions.tf             # Provider versions
├── terraform.tfvars        # Your configuration (gitignored)
│
└── modules/
    ├── iam/               # IAM roles and policies
    ├── s3/                # S3 buckets for data lake
    ├── dms/               # DMS replication
    ├── glue/              # Glue catalog and crawlers
    └── athena/            # Athena workgroups and queries
```

## Cost Estimation

**Monthly costs (dev environment):**

| Service | Resource | Estimated Cost |
|---------|----------|----------------|
| DMS | t3.medium instance (24/7) | ~$70 |
| S3 | 100 GB storage | ~$2.30 |
| S3 | Requests | ~$5 |
| Glue | Crawlers (hourly) | ~$13 |
| Athena | 100 GB scanned | ~$0.50 |
| **Total** | | **~$90/month** |

**Cost optimization:**
- Stop DMS instance when not testing
- Use lifecycle policies on S3
- Run crawlers on-demand instead of scheduled

## Networking Options

### Option A: Local Django with ngrok (Testing)

```bash
# Install ngrok
brew install ngrok  # macOS

# Expose PostgreSQL
ngrok tcp 5432

# Use ngrok URL in terraform.tfvars
source_db_host = "0.tcp.ngrok.io"
source_db_port = 12345  # Port from ngrok
```

### Option B: Django on EC2 (Recommended)

1. Launch EC2 instance in same VPC as DMS
2. Deploy Django using Docker
3. Use private IP in terraform.tfvars
4. Update DMS security group to allow PostgreSQL access

### Option C: RDS as Source (Alternative)

1. Create RDS PostgreSQL instance
2. Restore Django database to RDS
3. Use RDS endpoint in terraform.tfvars

## Troubleshooting

### DMS Connection Test Fails

```bash
# Check security groups
# Ensure DMS can reach PostgreSQL on port 5432

# Check PostgreSQL logs
docker-compose logs postgres

# Verify PostgreSQL is listening
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SELECT version();"
```

### Glue Crawler Fails

```bash
# Check S3 bucket has data
aws s3 ls s3://<bronze-bucket>/dms-data/ --profile ramses

# Check Glue role permissions
aws iam get-role --role-name <glue-role-name> --profile ramses
```

### Athena Query Fails

```bash
# Verify database exists
aws glue get-database --name lakehouse_poc_dev_bronze --profile ramses

# Check table exists
aws glue get-tables --database-name lakehouse_poc_dev_bronze --profile ramses
```

## Cleanup

To destroy all resources:

```bash
# Stop DMS task first
aws dms stop-replication-task \
  --replication-task-arn <task-arn> \
  --profile ramses

# Wait for task to stop
# Then destroy infrastructure
terraform destroy
```

**Note**: S3 buckets with data may fail to delete. Empty them first:

```bash
aws s3 rm s3://<bucket-name> --recursive --profile ramses
```

## Next Steps

After infrastructure is deployed:

1. ✅ Verify DMS replication is working
2. ✅ Run Glue crawlers to discover tables
3. ⏳ Create Glue ETL jobs for Silver layer
4. ⏳ Implement Gold layer aggregations
5. ⏳ Set up Lake Formation governance
6. ⏳ Create BI dashboards

## Useful Commands

```bash
# Format Terraform files
terraform fmt -recursive

# Validate configuration
terraform validate

# Show current state
terraform show

# List resources
terraform state list

# Get specific output
terraform output s3_buckets

# Refresh state
terraform refresh

# Import existing resource
terraform import aws_s3_bucket.bronze <bucket-name>
```

## Security Best Practices

- ✅ All S3 buckets have encryption enabled
- ✅ Public access blocked on all buckets
- ✅ IAM roles follow least privilege principle
- ✅ Sensitive variables marked as sensitive
- ✅ Credentials not stored in code
- ⚠️ DMS instance is publicly accessible (required for external PostgreSQL)
- ⚠️ Consider VPN or Direct Connect for production

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review AWS CloudWatch logs
3. Check Terraform state: `terraform show`
4. Verify AWS credentials: `aws sts get-caller-identity --profile ramses`
