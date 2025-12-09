# Test DMS Connection - Quick Guide

## Prerequisites Checklist

Before testing DMS connection, ensure:

- [x] PostgreSQL is running with SSL enabled
- [x] ngrok tunnel is active
- [x] DMS endpoint updated with current ngrok URL
- [x] DMS endpoint configured with `ssl_mode = "require"`
- [x] Terraform changes applied

## Step-by-Step Testing

### 1. Verify PostgreSQL SSL Status

```bash
cd django-backend
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SHOW ssl;"
```

**Expected:** `ssl | on`

### 2. Check ngrok Tunnel

```bash
curl -s http://localhost:4040/api/tunnels | python3 -m json.tool | grep public_url
```

**Expected:** `"public_url": "tcp://X.tcp.us-cal-1.ngrok.io:XXXXX"`

### 3. Test Local SSL Connection

```bash
PGSSLMODE=require psql -h localhost -p 5432 -U lakehouse_user -d lakehouse_poc -c "SELECT COUNT(*) FROM core_tenant;"
```

**Expected:** Returns count of tenants (e.g., 8)

### 4. Test ngrok SSL Connection

```bash
# Replace with your actual ngrok host and port
PGSSLMODE=require psql -h 0.tcp.us-cal-1.ngrok.io -p 17597 -U lakehouse_user -d lakehouse_poc -c "SELECT COUNT(*) FROM core_tenant;"
```

**Expected:** Returns count of tenants (e.g., 8)

### 5. Verify Terraform Configuration

```bash
cd terraform-infra
grep -A 2 "source_db_host" terraform.tfvars
```

**Expected:** Should match current ngrok URL

### 6. Test DMS Endpoint (AWS CLI)

```bash
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-east-1:354918365317:rep:GKJLP2DBJRB5RICOWQS2FY6INM \
  --endpoint-arn arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI
```

**Expected:** Connection test starts successfully

### 7. Check Connection Test Status

```bash
aws dms describe-connections \
  --filters "Name=endpoint-arn,Values=arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI" \
  --query 'Connections[0].[Status,LastFailureMessage]' \
  --output table
```

**Expected:** `Status: successful`

## Alternative: Test via AWS Console

1. Go to AWS DMS Console: https://console.aws.amazon.com/dms/
2. Navigate to **Endpoints**
3. Select `lakehouse-poc-dev-source-postgres`
4. Click **Test connection**
5. Select replication instance: `lakehouse-poc-dev-dms`
6. Click **Run test**
7. Wait for result (should show "successful")

## Common Issues and Solutions

### Issue: "timeout expired"

**Possible Causes:**
- ngrok tunnel not running
- Wrong ngrok URL in terraform.tfvars
- Network connectivity issue

**Solution:**
```bash
# Check ngrok
ps aux | grep ngrok

# Get current URL
curl http://localhost:4040/api/tunnels

# Update terraform.tfvars and apply
cd terraform-infra
terraform apply -auto-approve
```

### Issue: "SSL connection required"

**Possible Causes:**
- PostgreSQL SSL not enabled
- DMS endpoint not configured for SSL

**Solution:**
```bash
# Check PostgreSQL SSL
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SHOW ssl;"

# If off, restart containers
docker-compose down
docker-compose up -d

# Verify DMS endpoint SSL mode
grep ssl_mode terraform-infra/modules/dms/main.tf
# Should be: ssl_mode = "require"
```

### Issue: "Access denied"

**Possible Causes:**
- Wrong credentials
- User doesn't have permissions

**Solution:**
```bash
# Verify credentials in .env
cat django-backend/.env | grep DATABASE

# Test credentials locally
psql -h localhost -p 5432 -U lakehouse_user -d lakehouse_poc -c "SELECT 1;"
```

### Issue: "Database does not exist"

**Possible Causes:**
- Wrong database name
- Database not created

**Solution:**
```bash
# List databases
docker-compose exec postgres psql -U lakehouse_user -l

# Check terraform.tfvars
grep source_db_name terraform-infra/terraform.tfvars
```

## Success Indicators

When everything is working correctly, you should see:

✅ PostgreSQL SSL: `on`
✅ ngrok tunnel: Active with public URL
✅ Local SSL connection: Successful
✅ ngrok SSL connection: Successful
✅ Terraform config: Matches current ngrok URL
✅ DMS endpoint test: `Status: successful`

## Next Steps After Successful Connection

Once the DMS endpoint test passes:

### 1. Start Replication Task

```bash
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:us-east-1:354918365317:task:Y2YMQI2SJZGGHKCQTPU2LUM25A \
  --start-replication-task-type start-replication
```

### 2. Monitor Progress

```bash
# Check status
aws dms describe-replication-tasks \
  --filters "Name=replication-task-id,Values=lakehouse-poc-dev-task" \
  --query 'ReplicationTasks[0].[Status,ReplicationTaskStats]' \
  --output table

# View logs
aws logs tail /aws/dms/tasks/lakehouse-poc-dev-task --follow
```

### 3. Verify Data in S3

```bash
# Wait a few minutes, then check S3
aws s3 ls s3://lakehouse-poc-dev-bronze-arundlxp/dms-data/ --recursive
```

## Quick Troubleshooting Commands

```bash
# All-in-one health check
echo "=== PostgreSQL SSL ===" && \
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SHOW ssl;" && \
echo "=== ngrok Status ===" && \
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" && \
echo "=== Terraform Config ===" && \
grep -A 1 "source_db_host" terraform-infra/terraform.tfvars
```

## Support Resources

- [TROUBLESHOOTING_DMS.md](TROUBLESHOOTING_DMS.md) - Detailed troubleshooting guide
- [SSL_SETUP.md](django-backend/SSL_SETUP.md) - SSL configuration guide
- [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - Infrastructure overview
- [NEXT_STEPS.md](NEXT_STEPS.md) - Complete pipeline guide

---

**Ready to test?** Start with Step 1 above and work through each verification step.
