#!/bin/bash

# Task Tracker - Start Script
# This script starts all services using Docker Compose
#
# Usage:
#   ./start.sh           # Start production (default for backward compatibility)
#   ./start.sh prod      # Start production explicitly
#   ./start.sh dev       # Start development explicitly
#
# SIMPLEST: Just run Docker Compose directly (starts development):
#   docker compose up -d
#
# RECOMMENDED: Use Makefile for better control:
#   make prod-start      # Start production
#   make dev-start       # Start development
#   make start-all       # Start both environments

set -e

# Default to production for backward compatibility
ENV="${1:-prod}"

echo "🚀 Starting Task Tracker ($ENV environment)..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Determine which compose files to use
if [ "$ENV" = "dev" ] || [ "$ENV" = "development" ]; then
    PROJECT_NAME="tasktracker_dev"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
    FRONTEND_PORT="3001"
    BACKEND_PORT="6002"
    DB_PORT="5433"
    ENV_LABEL="Development"
elif [ "$ENV" = "prod" ] || [ "$ENV" = "production" ]; then
    PROJECT_NAME="tasktracker_prod"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    FRONTEND_PORT="3000"
    BACKEND_PORT="6001"
    DB_PORT="5432"
    ENV_LABEL="Production"
else
    echo "❌ Invalid environment: $ENV"
    echo "Usage: ./start.sh [prod|dev]"
    exit 1
fi

# Build and start services
echo "📦 Building and starting $ENV_LABEL services..."
docker compose -p "$PROJECT_NAME" $COMPOSE_FILES up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are healthy
echo ""
echo "🔍 Checking service status..."
docker compose -p "$PROJECT_NAME" $COMPOSE_FILES ps

echo ""
echo "✅ Task Tracker ($ENV_LABEL) is running!"
echo ""
echo "🌐 Frontend:  http://localhost:$FRONTEND_PORT"
echo "🔧 Backend:   http://localhost:$BACKEND_PORT"
echo "📚 API Docs:  http://localhost:$BACKEND_PORT/docs"
echo "🗄️  Database:  localhost:$DB_PORT"
echo ""
echo "💡 TIP: Use Makefile for better control:"
echo "   make prod-start, make dev-start, make status, etc."
echo ""
echo "To stop: ./stop.sh $ENV or docker compose -p $PROJECT_NAME $COMPOSE_FILES down"
echo "To view logs: docker compose -p $PROJECT_NAME $COMPOSE_FILES logs -f"
