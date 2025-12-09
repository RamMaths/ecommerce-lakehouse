# PostgreSQL SSL/TLS Setup Guide

## Overview

This guide explains how to enable SSL/TLS encryption for PostgreSQL connections, which is required for AWS DMS when connecting to PostgreSQL 15+.

## Why SSL is Required

- **AWS DMS Requirement**: PostgreSQL 15+ requires SSL/TLS for secure connections
- **Security**: Encrypts data in transit between client and server
- **Compliance**: Meets security standards for data protection
- **Best Practice**: Industry standard for database connections

## Quick Setup

### 1. Generate SSL Certificates

```bash
cd django-backend
./scripts/setup-ssl.sh
```

This creates:
- `ssl/server.key` - Private key (600 permissions)
- `ssl/server.crt` - Server certificate
- `ssl/root.crt` - Root certificate (for clients)

### 2. Restart PostgreSQL

```bash
docker-compose down
docker-compose up -d
```

### 3. Verify SSL is Enabled

```bash
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SHOW ssl;"
```

Expected output:
```
 ssl 
-----
 on
(1 row)
```

### 4. Test SSL Connection

Local connection:
```bash
PGSSLMODE=require psql -h localhost -p 5432 -U lakehouse_user -d lakehouse_poc
```

Through ngrok:
```bash
PGSSLMODE=require psql -h <ngrok-host> -p <ngrok-port> -U lakehouse_user -d lakehouse_poc
```

## Configuration Details

### Docker Compose Changes

The `docker-compose.yml` now includes:

```yaml
volumes:
  - ./ssl/server.crt:/var/lib/postgresql/server.crt:ro
  - ./ssl/server.key:/var/lib/postgresql/server.key:ro

command:
  - "-c"
  - "ssl=on"
  - "-c"
  - "ssl_cert_file=/var/lib/postgresql/server.crt"
  - "-c"
  - "ssl_key_file=/var/lib/postgresql/server.key"
```

### DMS Endpoint Configuration

The Terraform DMS endpoint now uses:

```hcl
ssl_mode = "require"  # SSL enabled for PostgreSQL 15+
```

## SSL Modes

PostgreSQL supports different SSL modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `disable` | No SSL | Development only |
| `allow` | Try SSL, fallback to non-SSL | Not recommended |
| `prefer` | Try SSL first | Not recommended |
| `require` | Require SSL, no certificate verification | **Current setup** |
| `verify-ca` | Require SSL + verify CA | Production |
| `verify-full` | Require SSL + verify CA + hostname | Production |

## Troubleshooting

### Issue: "SSL is off"

**Solution:**
```bash
# Ensure certificates exist
ls -la django-backend/ssl/

# Restart containers (not just restart)
docker-compose down
docker-compose up -d

# Verify
docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c "SHOW ssl;"
```

### Issue: "Permission denied for server.key"

**Cause:** PostgreSQL requires strict permissions on the key file

**Solution:**
```bash
chmod 600 django-backend/ssl/server.key
docker-compose restart postgres
```

### Issue: "Certificate verify failed"

**Cause:** Self-signed certificate not trusted

**Solution:** Use `sslmode=require` instead of `verify-ca` or `verify-full`

### Issue: DMS Connection Still Fails

**Checklist:**
1. ✅ SSL is enabled in PostgreSQL: `SHOW ssl;`
2. ✅ Local SSL connection works: `PGSSLMODE=require psql ...`
3. ✅ ngrok tunnel is running: `curl http://localhost:4040/api/tunnels`
4. ✅ ngrok SSL connection works: `PGSSLMODE=require psql -h <ngrok-host> ...`
5. ✅ DMS endpoint has `ssl_mode = "require"`
6. ✅ Terraform applied: `terraform apply`

## Production Considerations

### Use Proper Certificates

For production, use certificates from a trusted CA:

```bash
# Example with Let's Encrypt
certbot certonly --standalone -d your-domain.com

# Copy certificates
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/server.crt
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/server.key
```

### Enable Certificate Verification

Update DMS endpoint:

```hcl
ssl_mode = "verify-full"

# Add CA certificate
certificate_arn = aws_acm_certificate.postgres_cert.arn
```

### Rotate Certificates

Set up automatic certificate rotation:

```bash
# Add to crontab
0 0 1 * * /path/to/renew-certs.sh && docker-compose restart postgres
```

## Security Best Practices

1. **Never commit certificates to git**
   - Already in `.gitignore`
   - Use secrets management in production

2. **Use strong key sizes**
   - Minimum 2048-bit RSA keys
   - Consider 4096-bit for production

3. **Set certificate expiration**
   - Current setup: 365 days
   - Production: Use shorter periods (90 days)

4. **Restrict key file permissions**
   - `chmod 600` for private keys
   - `chmod 644` for certificates

5. **Use certificate verification in production**
   - `verify-ca` or `verify-full` modes
   - Validate certificate chain

## Testing SSL Connection

### From Python (Django)

```python
import psycopg2

conn = psycopg2.connect(
    host="0.tcp.us-cal-1.ngrok.io",
    port=17597,
    database="lakehouse_poc",
    user="lakehouse_user",
    password="secure_password",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
```

### From psql

```bash
# With SSL required
psql "postgresql://lakehouse_user@0.tcp.us-cal-1.ngrok.io:17597/lakehouse_poc?sslmode=require"

# With SSL disabled (should fail if SSL is required)
psql "postgresql://lakehouse_user@0.tcp.us-cal-1.ngrok.io:17597/lakehouse_poc?sslmode=disable"
```

### From DMS

Test the endpoint in AWS Console or CLI:

```bash
aws dms test-connection \
  --replication-instance-arn <your-instance-arn> \
  --endpoint-arn <your-endpoint-arn>
```

## Certificate Information

View certificate details:

```bash
# View certificate
openssl x509 -in ssl/server.crt -text -noout

# Check expiration
openssl x509 -in ssl/server.crt -noout -enddate

# Verify certificate and key match
openssl x509 -noout -modulus -in ssl/server.crt | openssl md5
openssl rsa -noout -modulus -in ssl/server.key | openssl md5
```

## Monitoring SSL Connections

Check active SSL connections:

```sql
SELECT 
  pid,
  usename,
  application_name,
  client_addr,
  ssl,
  ssl_version,
  ssl_cipher
FROM pg_stat_ssl
JOIN pg_stat_activity USING (pid)
WHERE ssl = true;
```

## References

- [PostgreSQL SSL Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [AWS DMS SSL Documentation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.SSL.html)
- [OpenSSL Documentation](https://www.openssl.org/docs/)

## Summary

✅ SSL/TLS is now enabled for PostgreSQL
✅ Self-signed certificates generated
✅ Docker Compose configured for SSL
✅ DMS endpoint updated to require SSL
✅ Tested locally and through ngrok

Your PostgreSQL database is now ready for secure connections with AWS DMS!
