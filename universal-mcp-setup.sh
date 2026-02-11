#!/bin/bash
set -e

echo "🔐 Task Tracker MCP Universal Setup"
echo "====================================="
echo ""

# Prompt for info
read -p "Enter your name: " NAME
read -p "Enter your email: " EMAIL
read -p "Enter your user ID (check database): " USER_ID
read -sp "Enter your password (will be created if new): " PASSWORD
echo ""

# Try to register (will fail if exists, that's OK)
echo "📝 Attempting registration..."
curl -s -X POST http://localhost:6001/api/auth/register \
  -H "Content-Type: application/json" \
  --data-binary "{\"name\":\"$NAME\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null 2>&1 || true

# Login
echo "🔑 Logging in..."
LOGIN_RESP=$(curl -s -X POST http://localhost:6001/api/auth/login \
  -H "Content-Type: application/json" \
  --data-binary "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  echo "Response: $LOGIN_RESP"
  exit 1
fi

# Create API key
echo "🔧 Creating API key..."
KEY_RESP=$(curl -s -X POST http://localhost:6001/api/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary '{"name":"MCP Server Key","expires_days":365}')

API_KEY=$(echo "$KEY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('key',''))" 2>/dev/null)

if [ -z "$API_KEY" ]; then
  echo "❌ API key creation failed!"
  echo "Response: $KEY_RESP"
  exit 1
fi

# Output configuration
echo ""
echo "✅ SUCCESS!"
echo "=========="
echo ""
echo "📋 Your API Key: $API_KEY"
echo ""
echo "⚠️  SAVE THIS KEY - shown only once!"
echo ""
echo "📝 ~/.claude/mcp_configs/task-tracker-local.json:"
echo ""
cat << EOF
{
  "mcpServers": {
    "task-tracker": {
      "command": "python",
      "args": ["$(pwd)/mcp-server/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "http://localhost:6001",
        "TASK_TRACKER_API_KEY": "$API_KEY",
        "TASK_TRACKER_USER_ID": "$USER_ID",
        "TASK_TRACKER_USER_NAME": "$NAME",
        "TASK_TRACKER_USER_EMAIL": "$EMAIL"
      }
    }
  }
}
EOF
echo ""
echo "🎉 Setup complete! Restart Claude Code to use the MCP server."
