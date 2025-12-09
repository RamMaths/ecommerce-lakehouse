#!/bin/bash

# Script to generate SSL certificates for PostgreSQL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="$SCRIPT_DIR/../ssl"

echo "🔐 Setting up SSL certificates for PostgreSQL..."

# Create SSL directory
mkdir -p "$SSL_DIR"
cd "$SSL_DIR"

# Generate private key
echo "📝 Generating private key..."
openssl genrsa -out server.key 2048
chmod 600 server.key

# Generate certificate signing request
echo "📝 Generating certificate signing request..."
openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 365 days)
echo "📝 Generating self-signed certificate..."
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

# Set proper permissions
chmod 600 server.key
chmod 644 server.crt

# Create root certificate (same as server cert for self-signed)
cp server.crt root.crt

echo "✅ SSL certificates generated successfully!"
echo ""
echo "Files created in $SSL_DIR:"
ls -lh "$SSL_DIR"
echo ""
echo "Next steps:"
echo "1. Restart PostgreSQL: docker-compose restart postgres"
echo "2. Test SSL connection: psql 'postgresql://lakehouse_user@localhost:5432/lakehouse_poc?sslmode=require'"
