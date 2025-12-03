# Deployment Checklist

Track your progress deploying the lakehouse POC.

## Pre-Deployment

- [ ] Django backend is running
- [ ] PostgreSQL has data seeded (medium scale)
- [ ] PostgreSQL publication created (`dms_publication`)
- [ ] ngrok installed
- [ ] AWS CLI configured with profile "ramses"
- [ ] Terraform installed

## ngrok Setup

- [ ] Signed up for ngrok account
- [ ] Got authtoken from dashboard
- [ ] Configured ngrok: `ngrok config add-authtoken YOUR_TOKEN`
- [ ] Started ngrok tunnel: `./start-ngrok-tunnel.sh`
- [ ] Noted ngrok host and port
- [ ] Tested connection through ngrok

## Terraform Configuration

- [ ] Copied `terraform.tfvars.example` to `terraform.tfvars`
- [ ] Updated `source_db_host` with ngrok host
- [ ] Updated `source_db_port` with ngrok port
- [ ] Updated `source_db_password` with actual password
- [ ] Updated `owner` with your name

## Terraform Deployment

- [ ] Ran `terraform init`
- [ ] Ran `terraform plan` and reviewed
- [ ] Ran `terraform apply` and confirmed
- [ ] Waited for deployment to complete (~15 minutes)
- [ ] Checked `terraform output` for resource details

## Post-Deployment Verification

- [ ] Verified S3 buckets created
- [ ] Checked DMS instance status is "available"
- [ ] Tested DMS source endpoint connection
- [ ] Started DMS replication task
- [ ] Verified data in Bronze S3 bucket
- [ ] Ran Glue Bronze crawler
- [ ] Verified tables in Glue Data Catalog
- [ ] Ran test query in Athena
- [ ] Tested named queries

## Testing

- [ ] Tested CDC by adding new record in Django
- [ ] Verified new record appears in S3
- [ ] Ran revenue by tenant query
- [ ] Ran customer acquisition query
- [ ] Ran event funnel query
- [ ] Checked ngrok web interface (http://localhost:4040)

## Documentation

- [ ] Documented ngrok connection details
- [ ] Saved Terraform outputs
- [ ] Noted any issues encountered
- [ ] Took screenshots for presentation

## Optional Enhancements

- [ ] Created Glue ETL job for Silver layer
- [ ] Implemented Gold layer aggregations
- [ ] Set up Lake Formation permissions
- [ ] Created QuickSight dashboard
- [ ] Set up CloudWatch alarms
- [ ] Configured cost alerts

## Cleanup (When Done)

- [ ] Stopped DMS replication task
- [ ] Ran `terraform destroy`
- [ ] Stopped ngrok tunnel
- [ ] Stopped Django backend
- [ ] Deleted S3 data (if needed)

---

## Quick Reference

### Important URLs

- ngrok Dashboard: https://dashboard.ngrok.com/
- ngrok Web Interface: http://localhost:4040
- AWS Console: https://console.aws.amazon.com/
- Athena Console: https://console.aws.amazon.com/athena/
- DMS Console: https://console.aws.amazon.com/dms/
- Glue Console: https://console.aws.amazon.com/glue/

### Important Commands

```bash
# Start ngrok
./start-ngrok-tunnel.sh

# Deploy Terraform
cd terraform-infra
terraform apply

# Check DMS status
aws dms describe-replication-tasks --profile ramses

# Start replication
aws dms start-replication-task \
  --replication-task-arn <arn> \
  --start-replication-task-type start-replication \
  --profile ramses

# Run crawler
aws glue start-crawler \
  --name lakehouse-poc-dev-bronze-crawler \
  --profile ramses

# Query in Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM core_tenant" \
  --query-execution-context Database=lakehouse_poc_dev_bronze \
  --result-configuration OutputLocation=s3://<bucket>/query-results/ \
  --work-group lakehouse-poc-dev-workgroup \
  --profile ramses
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| ngrok expired | Restart ngrok, update terraform.tfvars, run terraform apply |
| DMS connection fails | Check PostgreSQL is running, verify ngrok tunnel |
| No data in S3 | Check DMS task status, review CloudWatch logs |
| Glue crawler fails | Verify S3 has data, check IAM permissions |
| Athena query fails | Verify database exists, check table schema |

---

**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

**Started**: ___________

**Completed**: ___________

**Total Time**: ___________

**Issues Encountered**: 

___________________________________________

___________________________________________

___________________________________________
