#!/bin/bash
# Quick MCP setup - just provide your API key

set -e

echo "🚀 Quick Task Tracker MCP Setup"
echo "================================"
echo ""

# Check if API key is provided
if [ -z "$1" ]; then
  echo "Usage: ./setup-mcp-quick.sh YOUR_API_KEY YOUR_USER_ID"
  echo ""
  echo "Example:"
  echo "  ./setup-mcp-quick.sh ttk_live_abc123... 19"
  echo ""
  echo "Don't have an API key? Run: ./universal-mcp-setup.sh"
  exit 1
fi

API_KEY="$1"
USER_ID="${2:-0}"

# Get user info from API
echo "🔍 Fetching your user info..."
USER_INFO=$(curl -s http://localhost:6001/api/auth/me \
  -H "X-API-Key: $API_KEY")

if echo "$USER_INFO" | grep -q '"id"'; then
  USER_ID=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  USER_NAME=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
  USER_EMAIL=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email',''))" 2>/dev/null)

  echo "✅ Found user: $USER_NAME ($USER_EMAIL)"
else
  echo "❌ Invalid API key or API is down"
  exit 1
fi

# Warn if placeholder found in committed files
if [ -f ".mcp.json" ] && grep -q "SET_YOUR_API_KEY_HERE" .mcp.json; then
  echo "⚠️  WARNING: .mcp.json contains placeholder"
  echo "    Use .mcp.local.json instead (gitignored)"
  echo ""
fi

# Create config directory
mkdir -p ~/.claude/mcp_configs

# Write config
cat > ~/.claude/mcp_configs/task-tracker-local.json << EOF
{
  "mcpServers": {
    "task-tracker": {
      "command": "python3",
      "args": ["$(pwd)/mcp-server/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "http://localhost:6001",
        "TASK_TRACKER_API_KEY": "$API_KEY",
        "TASK_TRACKER_USER_ID": "$USER_ID",
        "TASK_TRACKER_USER_NAME": "$USER_NAME",
        "TASK_TRACKER_USER_EMAIL": "$USER_EMAIL"
      }
    }
  }
}
EOF

echo ""
echo "✅ MCP Configuration saved!"
echo ""
echo "📍 Location: ~/.claude/mcp_configs/task-tracker-local.json"
echo ""
echo "🎉 Next steps:"
echo "   1. Restart Claude Code"
echo "   2. Test with: mcp__task-tracker__list_projects()"
echo ""
