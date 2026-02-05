#!/bin/bash

# Task Tracker - Start Script
# This script starts all services using Docker Compose

set -e

echo "🚀 Starting Task Tracker..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start services
echo "📦 Building and starting services..."
docker compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are healthy
echo ""
echo "🔍 Checking service status..."
docker compose ps

echo ""
echo "✅ Task Tracker is running!"
echo ""
echo "🌐 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:6001"
echo "📚 API Docs:  http://localhost:6001/docs"
echo "🤖 MCP Server: http://localhost:6000/sse"
echo "🗄️  Database:  localhost:5432"
echo ""
echo "To connect MCP to Claude Desktop, add to your config:"
echo '  "task-tracker": { "url": "http://localhost:6000/sse", "transport": "sse" }'
echo ""
echo "To stop: ./stop.sh or docker compose down"
echo "To view logs: docker compose logs -f"
