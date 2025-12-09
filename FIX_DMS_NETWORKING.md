# Fix DMS Networking Issues - Complete Guide

## Root Cause Analysis

Your DMS replication instance cannot reach the external ngrok endpoint due to network configuration issues:

### Current Setup
- **DMS Instance**: `lakehouse-poc-dev-dms`
- **VPC**: `vpc-0f7e00ab54664548f` (default VPC, CIDR: 172.31.0.0/16)
- **Private IP**: 172.31.102.204
- **Security Group**: `sg-0414961fb22502fd8`
- **Public Access**: Disabled (as configured)
- **Target**: External ngrok endpoint `0.tcp.us-cal-1.ngrok.io:17597`

### The Problem
1. DMS instance is in a **private subnet** without internet access
2. Security group may lack proper **outbound rules**
3. VPC may be missing **Internet Gateway** or **NAT Gateway** routing
4. ngrok endpoint requires **external internet connectivity**

---

## Solution Options

### Option 1: Enable Public Access for DMS (Quickest Fix)

This is the fastest solution for POC/testing purposes.

#### Step 1: Update Terraform Configuration

Edit `terraform-infra/modules/dms/main.tf`:

```hcl
resource "aws_dms_replication_instance" "main" {
  replication_instance_id   = "${var.project_name}-${var.environment}-dms"
  replication_instance_class = var.dms_instance_class
  allocated_storage          = var.dms_allocated_storage
  
  multi_az                   = false
  publicly_accessible        = true  # Changed from false to true
  
  replication_subnet_group_id = aws_dms_replication_subnet_group.main.id
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-dms-instance"
  })
}
```

#### Step 2: Apply Changes

```bash
cd terraform-infra
terraform apply -auto-approve
```

**Note:** This will recreate the DMS instance (takes ~10 minutes)

#### Step 3: Test Connection

```bash
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-east-1:354918365317:rep:GKJLP2DBJRB5RICOWQS2FY6INM \
  --endpoint-arn arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI
```

---

### Option 2: Add NAT Gateway (Production-Ready)

Keep DMS private but add NAT Gateway for outbound internet access.

#### Step 1: Create NAT Gateway Module

Create `terraform-infra/modules/networking/main.tf`:

```hcl
# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get public subnet (for NAT Gateway)
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  
  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

# Allocate Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-nat-eip"
  })
}

# Create NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = data.aws_subnets.public.ids[0]
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-nat-gateway"
  })
}

# Update route table for DMS subnets
resource "aws_route" "nat_gateway" {
  route_table_id         = data.aws_route_table.dms.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

# Get route table for DMS subnets
data "aws_route_table" "dms" {
  subnet_id = var.dms_subnet_id
}
```

**Cost:** ~$32/month for NAT Gateway

---

### Option 3: Update Security Group Rules (May Not Be Sufficient)

Even with security group updates, you still need internet routing.

#### Check Current Rules

```bash
aws ec2 describe-security-groups \
  --group-ids sg-0414961fb22502fd8 \
  --query 'SecurityGroups[0].IpPermissionsEgress' \
  --output table
```

#### Add Outbound Rule

```bash
aws ec2 authorize-security-group-egress \
  --group-id sg-0414961fb22502fd8 \
  --protocol tcp \
  --port 17597 \
  --cidr 0.0.0.0/0
```

Or allow all outbound (common for DMS):

```bash
aws ec2 authorize-security-group-egress \
  --group-id sg-0414961fb22502fd8 \
  --protocol -1 \
  --cidr 0.0.0.0/0
```

---

### Option 4: Use AWS Systems Manager Session Manager (Alternative)

Instead of ngrok, use SSM to create a tunnel.

#### Prerequisites
- Install AWS Systems Manager agent on database server
- Configure IAM roles for SSM

#### Create Tunnel

```bash
aws ssm start-session \
  --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'
```

---

## Recommended Solution for POC

**Use Option 1: Enable Public Access**

### Why?
- ✅ Fastest to implement (5 minutes)
- ✅ No additional costs
- ✅ Works with ngrok immediately
- ✅ Suitable for POC/testing
- ⚠️ Not recommended for production

### Implementation Steps

#### 1. Update Terraform

```bash
cd terraform-infra/modules/dms
```

Edit `main.tf` and change:
```hcl
publicly_accessible = true  # Line ~48
```

#### 2. Apply Changes

```bash
cd terraform-infra
terraform apply -auto-approve
```

**Expected output:**
```
Plan: 1 to add, 0 to change, 1 to destroy.
...
module.dms.aws_dms_replication_instance.main: Destroying...
module.dms.aws_dms_replication_instance.main: Creating...
module.dms.aws_dms_replication_instance.main: Creation complete after 10m
```

#### 3. Wait for Instance to be Available

```bash
aws dms describe-replication-instances \
  --filters "Name=replication-instance-id,Values=lakehouse-poc-dev-dms" \
  --query 'ReplicationInstances[0].[ReplicationInstanceStatus,PubliclyAccessible]' \
  --output table
```

Expected: `available | True`

#### 4. Test Connection

```bash
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-east-1:354918365317:rep:GKJLP2DBJRB5RICOWQS2FY6INM \
  --endpoint-arn arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI
```

#### 5. Check Test Status

```bash
aws dms describe-connections \
  --filters "Name=endpoint-arn,Values=arn:aws:dms:us-east-1:354918365317:endpoint:YGDZR2YU4FG3PL5LCFBPDNM5PI" \
  --query 'Connections[0].[Status,LastFailureMessage]' \
  --output table
```

Expected: `successful | None`

---

## Verification Checklist

Before testing DMS connection:

- [ ] ngrok tunnel is running
- [ ] PostgreSQL is accessible through ngrok
- [ ] SSL is enabled on PostgreSQL
- [ ] DMS instance is in "available" state
- [ ] DMS instance has internet connectivity (public or NAT)
- [ ] Security group allows outbound traffic
- [ ] Terraform variables match current ngrok URL

### Quick Verification Script

```bash
#!/bin/bash

echo "=== 1. Check ngrok ==="
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"

echo -e "\n=== 2. Test PostgreSQL via ngrok ==="
PGSSLMODE=require psql -h 0.tcp.us-cal-1.ngrok.io -p 17597 -U lakehouse_user -d lakehouse_poc -c "SELECT 1;" 2>&1 | head -3

echo -e "\n=== 3. Check DMS Instance Status ==="
aws dms describe-replication-instances \
  --filters "Name=replication-instance-id,Values=lakehouse-poc-dev-dms" \
  --query 'ReplicationInstances[0].[ReplicationInstanceStatus,PubliclyAccessible,ReplicationInstancePublicIpAddress]' \
  --output table

echo -e "\n=== 4. Check Security Group ==="
aws ec2 describe-security-groups \
  --group-ids sg-0414961fb22502fd8 \
  --query 'SecurityGroups[0].[GroupId,IpPermissionsEgress[0].IpProtocol]' \
  --output table
```

---

## Troubleshooting

### Issue: DMS Instance Recreation Takes Too Long

**Solution:** Check status periodically
```bash
watch -n 30 'aws dms describe-replication-instances --filters "Name=replication-instance-id,Values=lakehouse-poc-dev-dms" --query "ReplicationInstances[0].ReplicationInstanceStatus"'
```

### Issue: Connection Still Times Out After Making Public

**Possible Causes:**
1. Security group still blocking outbound
2. ngrok tunnel expired
3. PostgreSQL not accepting connections

**Debug Steps:**
```bash
# 1. Check DMS can reach internet
aws dms test-connection --replication-instance-arn <arn> --endpoint-arn <test-endpoint>

# 2. Verify ngrok is accessible
curl -v telnet://0.tcp.us-cal-1.ngrok.io:17597

# 3. Check PostgreSQL logs
docker-compose logs postgres | tail -50
```

### Issue: Terraform State Issues

**Solution:**
```bash
cd terraform-infra
terraform refresh
terraform plan
```

---

## Production Recommendations

For production deployments:

### 1. Use VPN or Direct Connect
- AWS Site-to-Site VPN: ~$36/month
- AWS Direct Connect: Starting at $216/month
- More reliable than ngrok
- Better security

### 2. Use AWS RDS
- Managed PostgreSQL service
- Built-in DMS integration
- No networking complexity
- Automatic backups and HA

### 3. Use PrivateLink
- Private connectivity between VPCs
- No internet exposure
- Highly secure
- ~$7.50/month per endpoint

### 4. Implement Network Monitoring
- VPC Flow Logs
- CloudWatch metrics
- AWS Network Firewall
- GuardDuty for threat detection

---

## Cost Comparison

| Solution | Monthly Cost | Setup Time | Security | Reliability |
|----------|--------------|------------|----------|-------------|
| Public DMS | $0 extra | 5 min | ⚠️ Low | ⭐⭐⭐ |
| NAT Gateway | ~$32 | 30 min | ✅ Medium | ⭐⭐⭐⭐ |
| VPN | ~$36 | 2 hours | ✅ High | ⭐⭐⭐⭐⭐ |
| Direct Connect | ~$216 | Days | ✅ Highest | ⭐⭐⭐⭐⭐ |
| RDS | ~$50+ | 1 hour | ✅ High | ⭐⭐⭐⭐⭐ |

---

## Next Steps

1. **Immediate:** Enable public access for DMS (Option 1)
2. **Test:** Verify DMS endpoint connection
3. **Start:** Begin replication task
4. **Monitor:** Check data flow to S3
5. **Plan:** Consider production networking solution

---

## Summary

The networking issue is preventing DMS from reaching your ngrok endpoint. The quickest fix is to enable public access on the DMS instance. This is acceptable for POC but should be replaced with a more secure solution (NAT Gateway, VPN, or RDS) for production.

**Recommended Action:** Update `publicly_accessible = true` in Terraform and apply changes.
