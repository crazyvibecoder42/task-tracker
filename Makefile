.PHONY: help prod-start prod-stop prod-logs prod-restart prod-reset prod-db dev-start dev-stop dev-logs dev-restart dev-reset dev-db start-all stop-all status clean

help:
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Task Tracker - Environment Management"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Production Commands (ports 3000/6001/5432):"
	@echo "  make prod-start     - Start production environment"
	@echo "  make prod-stop      - Stop production environment"
	@echo "  make prod-logs      - View production logs (follow mode)"
	@echo "  make prod-restart   - Restart production services"
	@echo "  make prod-reset     - ⚠️  Reset production database (ALL DATA LOST)"
	@echo ""
	@echo "Development Commands (ports 3001/6002/5433):"
	@echo "  make dev-start      - Start development environment"
	@echo "  make dev-stop       - Stop development environment"
	@echo "  make dev-logs       - View development logs (follow mode)"
	@echo "  make dev-restart    - Restart development services"
	@echo "  make dev-reset      - Reset development database"
	@echo ""
	@echo "Combined Operations:"
	@echo "  make start-all      - Start both production and development"
	@echo "  make stop-all       - Stop both environments"
	@echo "  make status         - Show status of all environments"
	@echo "  make clean          - Clean up stopped containers and orphans"
	@echo ""
	@echo "Database Access:"
	@echo "  make prod-db        - Connect to production database"
	@echo "  make dev-db         - Connect to development database"
	@echo "════════════════════════════════════════════════════════════"

# Production Environment
prod-start:
	@echo "🚀 Starting production environment..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
	@echo ""
	@echo "✅ Production environment started:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:6001"
	@echo "   Database: postgresql://taskuser:taskpass@localhost:5432/tasktracker"
	@echo ""
	@echo "💡 View logs: make prod-logs"

prod-stop:
	@echo "⏹️  Stopping production environment..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down
	@echo "✅ Production environment stopped"

prod-logs:
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml logs -f

prod-restart:
	@echo "🔄 Restarting production services..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml restart
	@echo "✅ Production services restarted"

prod-reset:
	@echo "⚠️  WARNING: This will delete ALL production data!"
	@echo "⚠️  Database volume 'postgres_data' will be removed"
	@echo ""
	@read -p "Type 'DELETE-PRODUCTION-DATA' to confirm: " confirm && [ "$$confirm" = "DELETE-PRODUCTION-DATA" ]
	@echo "🗑️  Destroying production environment and data..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down -v
	@echo "🚀 Rebuilding production environment with fresh database..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
	@echo "✅ Production environment reset complete"

prod-db:
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml exec postgres psql -U taskuser -d tasktracker

# Development Environment
dev-start:
	@echo "🚀 Starting development environment..."
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build
	@echo ""
	@echo "✅ Development environment started:"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:6002"
	@echo "   Database: postgresql://taskuser:taskpass@localhost:5433/tasktracker_dev"
	@echo ""
	@echo "💡 View logs: make dev-logs"

dev-stop:
	@echo "⏹️  Stopping development environment..."
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "✅ Development environment stopped"

dev-logs:
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml logs -f

dev-restart:
	@echo "🔄 Restarting development services..."
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml restart
	@echo "✅ Development services restarted"

dev-reset:
	@echo "🗑️  Resetting development database..."
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down -v
	@echo "🚀 Rebuilding development environment with fresh database..."
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build
	@echo "✅ Development environment reset complete"

dev-db:
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml exec postgres psql -U taskuser -d tasktracker_dev

# Combined Operations
start-all:
	@echo "🚀 Starting both production and development environments..."
	@$(MAKE) prod-start
	@echo ""
	@$(MAKE) dev-start

stop-all:
	@echo "⏹️  Stopping all environments..."
	@$(MAKE) prod-stop
	@$(MAKE) dev-stop
	@echo "✅ All environments stopped"

status:
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Environment Status"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Production (ports 3000/6001/5432):"
	@echo "────────────────────────────────────────────────────────────"
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml ps 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "Development (ports 3001/6002/5433):"
	@echo "────────────────────────────────────────────────────────────"
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml ps 2>/dev/null || echo "  Not running"
	@echo "════════════════════════════════════════════════════════════"

clean:
	@echo "🧹 Cleaning up stopped containers and orphans..."
	@docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
	@docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true
	@echo "✅ Cleanup complete"
