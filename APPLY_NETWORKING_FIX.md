# Apply DMS Networking Fix - Quick Guide

## What's Being Fixed

The DMS replication instance cannot reach the external ngrok endpoint because it's configured as private without internet access. We're enabling public access to allow it to connect to ngrok.

## Changes Made

**File:** `terraform-infra/modules/dms/main.tf`

**Change:**
```hcl
publicly_accessible = true  # Changed from false
```

## Apply the Fix

### Step 1: Navigate to Terraform Directory

```bash
cd terraform-infra
```

### Step 2: Review Changes

```bash
terraform plan
```

**Expected output:**
```
# module.dms.aws_dms_replication_instance.main must be replaced
-/+ resource "aws_dms_replication_instance" "main" {
      ~ publicly_accessible = false -> true # forces replacement
      ...
}

Plan: 1 to add, 0 to change, 1 to destroy.
```

### Step 3: Apply Changes

```bash
terraform apply -auto-approve
```

**⏱️ Expected Duration:** 10-15 minutes (DMS instance recreation)

**What happens:**
1. Terraform destroys the existing DMS instance
2. Creates a new instance with public access enabled
3. Replication task remains configured but stopped

### Step 4: Monitor Progress

In another terminal, watch the status:

```bash
watch -n 30 'aws dms describe-replication-instances \
  --filters "Name=replication-instance-id,Values=lakehouse-poc-dev-dms" \
  --query "ReplicationInstances[0].[ReplicationInstanceStatus,PubliclyAccessible]" \
  --output table'
```

**Status progression:**
- `creating` → `available`
- `PubliclyAccessible`: `False` → `True`

---

## Verify the Fix

### 1. Check DMS Instance Status

```bash
aws dms describe-replication-instances \
  --filters "Name=replication-instance-id,Values=lakehouse-poc-dev-dms" \
  --query 'ReplicationInstances[0].[ReplicationInstanceStatus,PubliclyAccessible,ReplicationInstancePublicIpAddress]' \
  --output table
```

**Expected:**
```
---------------------------------
|  available  |  True  | X.X.X.X |
---------------------------------
```

### 2. Test DMS Endpoint Connection

```bash
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-east-1:354918365317:rep:GKJLP2DBJRB5RICOWQS2FY6INM \
  --endpoint-arn arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI
```

### 3. Check Connection Test Result

Wait 1-2 minutes, then:

```bash
aws dms describe-connections \
  --filters "Name=endpoint-arn,Values=arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI" \
  --query 'Connections[0].[Status,LastFailureMessage]' \
  --output table
```

**Expected:**
```
-----------------------
|  successful  | None |
-----------------------
```

---

## If Connection Still Fails

### Check Prerequisites

```bash
# 1. Verify ngrok is running
ps aux | grep ngrok | grep -v grep

# 2. Get current ngrok URL
curl -s http://localhost:4040/api/tunnels | python3 -m json.tool | grep public_url

# 3. Test PostgreSQL through ngrok
PGSSLMODE=require psql -h 0.tcp.us-cal-1.ngrok.io -p 17597 -U lakehouse_user -d lakehouse_poc -c "SELECT 1;"

# 4. Verify terraform.tfvars matches ngrok URL
grep -A 1 "source_db_host" terraform.tfvars
```

### Update ngrok URL if Needed

If ngrok URL changed:

```bash
# Get current URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
HOST=$(echo $NGROK_URL | sed 's|tcp://||' | cut -d: -f1)
PORT=$(echo $NGROK_URL | sed 's|tcp://||' | cut -d: -f2)

echo "Current ngrok: $HOST:$PORT"

# Update terraform.tfvars
cd terraform-infra
sed -i.bak "s/source_db_host.*/source_db_host     = \"$HOST\"/" terraform.tfvars
sed -i.bak "s/source_db_port.*/source_db_port     = $PORT/" terraform.tfvars

# Apply
terraform apply -auto-approve
```

---

## After Successful Connection

### Start Replication Task

```bash
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:us-east-1:354918365317:task:Y2YMQI2SJZGGHKCQTPU2LUM25A \
  --start-replication-task-type start-replication
```

### Monitor Replication

```bash
# Check task status
aws dms describe-replication-tasks \
  --filters "Name=replication-task-id,Values=lakehouse-poc-dev-task" \
  --query 'ReplicationTasks[0].[Status,ReplicationTaskStats]' \
  --output json

# View logs
aws logs tail /aws/dms/tasks/lakehouse-poc-dev-task --follow
```

### Verify Data in S3

After a few minutes:

```bash
# List replicated files
aws s3 ls s3://lakehouse-poc-dev-bronze-arundlxp/dms-data/ --recursive

# Count files
aws s3 ls s3://lakehouse-poc-dev-bronze-arundlxp/dms-data/ --recursive | wc -l
```

---

## Rollback (If Needed)

If you need to revert:

```bash
cd terraform-infra/modules/dms
# Change back to: publicly_accessible = false
cd ../..
terraform apply -auto-approve
```

---

## Important Notes

### Security Considerations

⚠️ **Public DMS Instance:**
- Acceptable for POC/testing
- Not recommended for production
- Consider NAT Gateway or VPN for production

### Cost Impact

✅ **No additional cost** for making DMS public
- Same pricing as private instance
- Only DMS instance charges apply (~$100/month for t3.medium)

### Alternative Solutions

For production, consider:
1. **NAT Gateway** (~$32/month) - Keep DMS private with internet access
2. **VPN** (~$36/month) - Secure site-to-site connection
3. **AWS RDS** (~$50+/month) - Managed database with built-in DMS support

---

## Success Criteria

✅ DMS instance status: `available`
✅ Publicly accessible: `True`
✅ Endpoint test status: `successful`
✅ Replication task: `running`
✅ Data appearing in S3: `Yes`

---

## Timeline

| Step | Duration | Status |
|------|----------|--------|
| Terraform apply | 10-15 min | ⏳ In progress |
| Instance available | - | ⏳ Waiting |
| Test connection | 1-2 min | ⏳ Pending |
| Start replication | 1 min | ⏳ Pending |
| Data in S3 | 5-10 min | ⏳ Pending |

**Total:** ~20-30 minutes from start to data in S3

---

## Support

If issues persist after applying this fix:
- Check [FIX_DMS_NETWORKING.md](FIX_DMS_NETWORKING.md) for detailed troubleshooting
- Review [TROUBLESHOOTING_DMS.md](TROUBLESHOOTING_DMS.md) for common issues
- See [TEST_DMS_CONNECTION.md](TEST_DMS_CONNECTION.md) for verification steps

---

**Ready to apply?** Run `terraform apply -auto-approve` in the `terraform-infra` directory.
