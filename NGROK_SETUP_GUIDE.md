# ngrok Setup Guide for AWS DMS Testing

Complete guide to expose your local Django PostgreSQL to AWS using ngrok.

## What is ngrok?

ngrok creates a secure tunnel from a public URL to your local PostgreSQL, allowing AWS DMS to connect to your Django database running on your laptop.

## Step 1: Sign Up for ngrok (Free)

1. Go to https://ngrok.com/
2. Sign up for a free account
3. Get your authtoken from the dashboard

## Step 2: Configure ngrok

```bash
# Add your authtoken (get it from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

## Step 3: Start ngrok Tunnel

```bash
# Navigate to project root
cd ~/path/to/lakehouse-poc

# Start ngrok tunnel to PostgreSQL
ngrok tcp 5432
```

**Keep this terminal open!** ngrok must stay running for AWS DMS to connect.

## Step 4: Get Connection Details

After starting ngrok, you'll see output like:

```
Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    tcp://0.tcp.ngrok.io:12345 -> localhost:5432

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Important values:**
- **Host**: `0.tcp.ngrok.io` (or similar)
- **Port**: `12345` (or whatever port is shown)

## Step 5: Test Connection

Open a new terminal and test the connection:

```bash
# Test from your machine
psql -h 0.tcp.ngrok.io -p 12345 -U lakehouse_user -d lakehouse_poc
# Password: secure_password

# If successful, you should see:
# lakehouse_poc=>
```

## Step 6: Update Terraform Configuration

```bash
cd terraform-infra

# Edit terraform.tfvars
nano terraform.tfvars
```

Update with your ngrok details:

```hcl
# Django PostgreSQL Source Database (via ngrok)
source_db_host     = "0.tcp.ngrok.io"      # Your ngrok host
source_db_port     = 12345                  # Your ngrok port
source_db_name     = "lakehouse_poc"
source_db_username = "lakehouse_user"
source_db_password = "secure_password"      # Your actual password
```

## Step 7: Deploy Terraform

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Deploy (takes 10-15 minutes)
terraform apply
```

## Step 8: Monitor ngrok Traffic

While DMS is replicating, you can monitor connections:

1. Open ngrok web interface: http://localhost:4040
2. See all connections and requests in real-time
3. Useful for debugging connection issues

## Important Notes

### ⚠️ Limitations

- **Free tier**: Limited to 1 tunnel at a time
- **Session timeout**: Free tunnels expire after 2 hours (need to restart)
- **URL changes**: Each time you restart ngrok, you get a new URL
- **Not for production**: Only for testing/POC

### 💡 Tips

1. **Keep ngrok running**: Don't close the terminal
2. **Static domain**: Upgrade to paid plan for consistent URL
3. **Monitor usage**: Check ngrok dashboard for connection stats
4. **Security**: ngrok tunnels are encrypted (TLS)

### 🔒 Security

- ngrok tunnels are secure (TLS encrypted)
- Only you have access to the tunnel
- PostgreSQL credentials still required
- Consider IP whitelisting in production

## Troubleshooting

### Issue: "Failed to complete tunnel connection"

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart PostgreSQL if needed
cd django-backend
docker-compose restart postgres
```

### Issue: "Connection refused"

**Solution:**
```bash
# Verify PostgreSQL is listening
docker-compose exec postgres pg_isready -U lakehouse_user

# Check PostgreSQL logs
docker-compose logs postgres
```

### Issue: "Authentication failed"

**Solution:**
```bash
# Verify credentials
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SELECT 1;"

# Check password in .env file
cat .env | grep DATABASE_PASSWORD
```

### Issue: ngrok session expired

**Solution:**
```bash
# Restart ngrok (you'll get a new URL)
ngrok tcp 5432

# Update terraform.tfvars with new URL
# Run: terraform apply again
```

## Alternative: ngrok with Docker Compose

You can also add ngrok to your docker-compose.yml:

```yaml
services:
  # ... existing services ...
  
  ngrok:
    image: ngrok/ngrok:latest
    command: tcp postgres:5432
    environment:
      NGROK_AUTHTOKEN: your-auth-token-here
    ports:
      - "4040:4040"  # Web interface
    depends_on:
      - postgres
```

## Cost Comparison

| Option | Setup Time | Cost | Reliability | Best For |
|--------|------------|------|-------------|----------|
| ngrok (free) | 5 min | Free | Good | Testing/POC |
| ngrok (paid) | 5 min | $8/mo | Excellent | Short-term |
| EC2 Django | 30 min | ~$10/mo | Excellent | Long-term |
| RDS Source | 20 min | ~$15/mo | Excellent | Production |

## Next Steps

After ngrok is running and Terraform is deployed:

1. ✅ Test DMS source endpoint connection
2. ✅ Start DMS replication task
3. ✅ Monitor data flowing to S3
4. ✅ Run Glue crawler
5. ✅ Query data in Athena

## Useful Commands

```bash
# Start ngrok
ngrok tcp 5432

# Check ngrok status
curl http://localhost:4040/api/tunnels

# Get ngrok URL programmatically
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'

# Stop ngrok
# Press Ctrl+C in the ngrok terminal
```

## When to Stop Using ngrok

Consider moving to EC2 or RDS when:
- You need 24/7 availability
- ngrok session timeouts are annoying
- You want a static connection URL
- You're moving beyond POC phase

---

**Ready to start?** Run `ngrok tcp 5432` and follow the steps above!
