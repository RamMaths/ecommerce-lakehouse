#!/bin/bash

# Setup script for ngrok + Terraform deployment

set -e

echo "=========================================="
echo "  ngrok + Terraform Setup for Lakehouse POC"
echo "=========================================="
echo ""

# Check if Django is running
echo "🔍 Checking Django backend..."
if ! docker ps | grep -q lakehouse_postgres; then
    echo "❌ Django PostgreSQL is not running!"
    echo ""
    echo "Please start Django first:"
    echo "  cd django-backend"
    echo "  docker-compose up -d"
    echo ""
    exit 1
fi
echo "✅ Django PostgreSQL is running"
echo ""

# Check if ngrok is installed
echo "🔍 Checking ngrok installation..."
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed!"
    echo ""
    echo "Installing ngrok..."
    brew install ngrok/ngrok/ngrok
fi
echo "✅ ngrok is installed"
echo ""

# Check if ngrok is configured
echo "🔍 Checking ngrok configuration..."
if ! ngrok config check &> /dev/null; then
    echo "⚠️  ngrok is not configured with an authtoken"
    echo ""
    echo "Please follow these steps:"
    echo "1. Sign up at https://ngrok.com/"
    echo "2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "3. Run: ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    read -p "Press Enter after you've configured ngrok..."
fi
echo "✅ ngrok is configured"
echo ""

# Instructions for starting ngrok
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""
echo "1. Start ngrok tunnel (in a new terminal):"
echo "   ngrok tcp 5432"
echo ""
echo "2. Copy the connection details from ngrok output:"
echo "   - Host: (e.g., 0.tcp.ngrok.io)"
echo "   - Port: (e.g., 12345)"
echo ""
echo "3. Test the connection:"
echo "   psql -h <ngrok-host> -p <ngrok-port> -U lakehouse_user -d lakehouse_poc"
echo ""
echo "4. Update Terraform configuration:"
echo "   cd terraform-infra"
echo "   cp terraform.tfvars.example terraform.tfvars"
echo "   nano terraform.tfvars"
echo ""
echo "   Update these values:"
echo "   source_db_host = \"your-ngrok-host\""
echo "   source_db_port = your-ngrok-port"
echo ""
echo "5. Deploy infrastructure:"
echo "   terraform init"
echo "   terraform apply"
echo ""
echo "=========================================="
echo ""
echo "📖 For detailed instructions, see: NGROK_SETUP_GUIDE.md"
echo ""
