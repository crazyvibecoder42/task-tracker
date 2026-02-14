#!/bin/bash

# Task Tracker MCP Setup Script
# This script sets up the MCP configuration for the current repository
#
# Usage:
#   ./setup-mcp.sh           # Setup for production (default)
#   ./setup-mcp.sh prod      # Setup for production explicitly
#   ./setup-mcp.sh dev       # Setup for development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to production
ENV="${1:-prod}"

# Determine environment configuration
if [ "$ENV" = "dev" ] || [ "$ENV" = "development" ]; then
    API_URL="${TASK_TRACKER_API_URL:-http://localhost:6002}"
    MCP_CONFIG_FILE=".mcp.dev.json"
    MCP_SERVER_NAME="task-tracker-dev"
    ENV_LABEL="Development"
    COMPOSE_CMD="docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml"
elif [ "$ENV" = "prod" ] || [ "$ENV" = "production" ]; then
    API_URL="${TASK_TRACKER_API_URL:-http://localhost:6001}"
    MCP_CONFIG_FILE=".mcp.prod.json"
    MCP_SERVER_NAME="task-tracker-prod"
    ENV_LABEL="Production"
    COMPOSE_CMD="docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml"
else
    echo -e "${RED}❌ Invalid environment: $ENV${NC}"
    echo "Usage: ./setup-mcp.sh [prod|dev]"
    exit 1
fi

API_KEY_NAME="MCP Server Key ($ENV_LABEL) - $(date +%Y%m%d-%H%M%S)"
API_KEY_EXPIRY_DAYS=365

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Task Tracker MCP Setup${NC}"
    echo -e "${BLUE}  Environment: $ENV_LABEL${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if jq is installed
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed."
        echo "Please install jq:"
        echo "  - macOS: brew install jq"
        echo "  - Ubuntu/Debian: sudo apt-get install jq"
        echo "  - CentOS/RHEL: sudo yum install jq"
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed."
        exit 1
    fi
}

# Check if backend is running
check_backend() {
    print_info "Checking if backend is running at $API_URL..."

    if ! curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        print_error "Backend is not running at $API_URL"
        echo ""
        echo "Please start the backend with:"
        echo "  Production: make prod-start"
        echo "  Development: make dev-start"
        echo ""
        echo "Or manually:"
        echo "  $COMPOSE_CMD up -d"
        exit 1
    fi

    print_success "Backend is running"
}

# Get credentials from user
get_credentials() {
    echo ""
    read -p "Enter email: " EMAIL
    read -sp "Enter password: " PASSWORD
    echo ""

    if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
        print_error "Email and password are required"
        exit 1
    fi
}

# Login and get access token
login() {
    print_info "Logging in..."

    LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

    # Check if login was successful
    if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
        ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
        USER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.id')
        USER_NAME=$(echo "$LOGIN_RESPONSE" | jq -r '.user.name')
        print_success "Logged in as $USER_NAME (ID: $USER_ID)"
    else
        print_error "Login failed"
        ERROR_MSG=$(echo "$LOGIN_RESPONSE" | jq -r '.detail // "Unknown error"')
        echo "Error: $ERROR_MSG"
        exit 1
    fi
}

# Create API key
create_api_key() {
    print_info "Creating API key..."

    API_KEY_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/api-keys" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d "{\"name\":\"$API_KEY_NAME\",\"expires_days\":$API_KEY_EXPIRY_DAYS}")

    # Check if API key was created
    if echo "$API_KEY_RESPONSE" | jq -e '.key' > /dev/null 2>&1; then
        API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.key')
        KEY_ID=$(echo "$API_KEY_RESPONSE" | jq -r '.id')
        print_success "API key created (ID: $KEY_ID)"
    else
        print_error "Failed to create API key"
        ERROR_MSG=$(echo "$API_KEY_RESPONSE" | jq -r '.detail // "Unknown error"')
        echo "Error: $ERROR_MSG"
        exit 1
    fi
}

# Create MCP configuration file
create_mcp_config() {
    print_info "Creating $MCP_CONFIG_FILE..."

    # Check if file already exists
    if [ -f "$MCP_CONFIG_FILE" ]; then
        read -p "$(echo -e ${YELLOW}⚠${NC}) $MCP_CONFIG_FILE already exists. Overwrite? (y/N): " OVERWRITE
        if [ "$OVERWRITE" != "y" ] && [ "$OVERWRITE" != "Y" ]; then
            print_info "Aborted. Existing configuration preserved."
            exit 0
        fi
    fi

    # Create MCP configuration
    cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "$MCP_SERVER_NAME": {
      "command": "python3",
      "args": ["./mcp-server/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "$API_URL",
        "TASK_TRACKER_API_KEY": "$API_KEY",
        "TASK_TRACKER_USER_ID": "$USER_ID"
      }
    }
  }
}
EOF

    print_success "Created $MCP_CONFIG_FILE"
}

# Add to gitignore
update_gitignore() {
    if [ -f ".gitignore" ]; then
        if ! grep -q "^$MCP_CONFIG_FILE$" .gitignore; then
            print_info "Adding $MCP_CONFIG_FILE to .gitignore..."
            echo "" >> .gitignore
            echo "# MCP $ENV_LABEL configuration (contains secrets)" >> .gitignore
            echo "$MCP_CONFIG_FILE" >> .gitignore
            print_success "Updated .gitignore"
        fi
    fi
}

# Display summary
show_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}\n"

    echo "Configuration Details:"
    echo "  • Environment: $ENV_LABEL"
    echo "  • User: $USER_NAME (ID: $USER_ID)"
    echo "  • API URL: $API_URL"
    echo "  • API Key: ${API_KEY:0:20}... (saved to $MCP_CONFIG_FILE)"
    echo "  • Expires: $API_KEY_EXPIRY_DAYS days"
    echo "  • MCP Server Name: $MCP_SERVER_NAME"

    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "  1. Restart Claude Code for changes to take effect"
    echo "  2. Test MCP connection with: /help (in Claude Code)"
    echo "  3. Keep $MCP_CONFIG_FILE secure (already in .gitignore)"

    echo -e "\n${YELLOW}Note:${NC} The API key is stored in $MCP_CONFIG_FILE"
    echo "Do not commit this file to version control!"

    echo -e "\n${YELLOW}Multi-Environment Setup:${NC}"
    echo "You can set up both production and development MCP configs:"
    echo "  ./setup-mcp.sh prod   # Creates .mcp.prod.json"
    echo "  ./setup-mcp.sh dev    # Creates .mcp.dev.json"
}

# Main execution
main() {
    print_header
    check_dependencies
    check_backend
    get_credentials
    login
    create_api_key
    create_mcp_config
    update_gitignore
    show_summary
}

# Run main function
main
