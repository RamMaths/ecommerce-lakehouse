#!/bin/bash

# Setup script for Django backend

set -e

echo "=========================================="
echo "  Lakehouse POC - Django Backend Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  Please review .env and update if needed"
    echo ""
fi

# Start services
echo "🚀 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL
until docker-compose exec -T postgres pg_isready -U lakehouse_user > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done

echo "✓ PostgreSQL is ready"
echo ""

# Run migrations
echo "🔧 Running database migrations..."
docker-compose exec -T django python manage.py migrate

echo ""
echo "=========================================="
echo "  ✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Create a superuser:"
echo "   docker-compose exec django python manage.py createsuperuser"
echo ""
echo "2. Seed data:"
echo "   docker-compose exec django python manage.py seed_all --scale medium"
echo ""
echo "3. Create PostgreSQL publication for DMS:"
echo "   docker-compose exec postgres psql -U lakehouse_user -d lakehouse_poc -c \"CREATE PUBLICATION dms_publication FOR ALL TABLES;\""
echo ""
echo "4. Access Django admin:"
echo "   http://localhost:8000/admin"
echo ""
