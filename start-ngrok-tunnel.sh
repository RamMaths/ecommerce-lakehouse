#!/bin/bash

# Quick start script for ngrok tunnel

echo "=========================================="
echo "  Starting ngrok tunnel for PostgreSQL"
echo "=========================================="
echo ""

# Check if Django is running
if ! docker ps | grep -q lakehouse_postgres; then
    echo "❌ Django PostgreSQL is not running!"
    echo ""
    echo "Starting Django backend..."
    cd django-backend
    docker-compose up -d
    echo "✅ Django backend started"
    echo ""
    cd ..
fi

# Check if ngrok is configured
if [ ! -f "$HOME/Library/Application Support/ngrok/ngrok.yml" ]; then
    echo "⚠️  ngrok needs to be configured first!"
    echo ""
    echo "Steps to configure ngrok:"
    echo "1. Go to: https://dashboard.ngrok.com/signup"
    echo "2. Sign up for a free account"
    echo "3. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "4. Run this command:"
    echo ""
    echo "   ngrok config add-authtoken YOUR_TOKEN_HERE"
    echo ""
    echo "5. Then run this script again"
    echo ""
    exit 1
fi

echo "🚀 Starting ngrok tunnel..."
echo ""
echo "⚠️  IMPORTANT: Keep this terminal open!"
echo "   ngrok must stay running for AWS DMS to connect"
echo ""
echo "📊 Monitor connections at: http://localhost:4040"
echo ""
echo "=========================================="
echo ""

# Start ngrok
ngrok tcp 5432
