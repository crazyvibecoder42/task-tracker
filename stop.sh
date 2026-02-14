#!/bin/bash

# Task Tracker - Stop Script
#
# Usage:
#   ./stop.sh           # Stop production (default)
#   ./stop.sh prod      # Stop production explicitly
#   ./stop.sh dev       # Stop development
#   ./stop.sh all       # Stop both environments
#
# RECOMMENDED: Use Makefile instead:
#   make prod-stop      # Stop production
#   make dev-stop       # Stop development
#   make stop-all       # Stop both environments

set -e

# Default to production for backward compatibility
ENV="${1:-prod}"

if [ "$ENV" = "all" ]; then
    echo "🛑 Stopping all Task Tracker environments..."
    docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
    docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true
    echo "✅ All environments stopped."
    exit 0
fi

# Determine which compose files to use
if [ "$ENV" = "dev" ] || [ "$ENV" = "development" ]; then
    PROJECT_NAME="tasktracker_dev"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
    ENV_LABEL="Development"
elif [ "$ENV" = "prod" ] || [ "$ENV" = "production" ]; then
    PROJECT_NAME="tasktracker_prod"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    ENV_LABEL="Production"
else
    echo "❌ Invalid environment: $ENV"
    echo "Usage: ./stop.sh [prod|dev|all]"
    exit 1
fi

echo "🛑 Stopping Task Tracker ($ENV_LABEL)..."
docker compose -p "$PROJECT_NAME" $COMPOSE_FILES down

echo "✅ Task Tracker ($ENV_LABEL) stopped."
echo ""
echo "💡 TIP: Use 'make stop-all' to stop both environments at once"
