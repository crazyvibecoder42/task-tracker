#!/bin/bash
# Setup local (per-repo) MCP configuration

set -e

echo "📁 Task Tracker - Local MCP Setup"
echo "=================================="
echo ""

if [ -z "$1" ]; then
  echo "Usage: ./setup-local-mcp.sh YOUR_API_KEY"
  echo ""
  echo "This creates .mcp.local.json in THIS repository"
  echo "Each repo can have different user/API key"
  echo ""
  echo "Example:"
  echo "  ./setup-local-mcp.sh ttk_live_abc123..."
  echo ""
  echo "Don't have an API key? Run: ./universal-mcp-setup.sh"
  exit 1
fi

API_KEY="$1"

# Get user info from API
echo "🔍 Validating API key..."
USER_INFO=$(curl -s http://localhost:6001/api/auth/me \
  -H "X-API-Key: $API_KEY")

if echo "$USER_INFO" | grep -q '"id"'; then
  USER_ID=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  USER_NAME=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
  USER_EMAIL=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email',''))" 2>/dev/null)

  echo "✅ User: $USER_NAME ($USER_EMAIL)"
else
  echo "❌ Invalid API key or API is down"
  exit 1
fi

# Ensure .mcp.local.json is gitignored
if ! grep -q ".mcp.local.json" .gitignore 2>/dev/null; then
  echo ".mcp.local.json" >> .gitignore
  echo "📝 Added .mcp.local.json to .gitignore"
fi

# Write local config
cat > .mcp.local.json << EOF
{
  "mcpServers": {
    "task-tracker": {
      "type": "stdio",
      "command": "python3",
      "args": ["./mcp-server/stdio_server.py"],
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
echo "✅ Local MCP Configuration saved!"
echo ""
echo "📍 Location: $(pwd)/.mcp.local.json"
echo "🔒 Security: File is gitignored (won't be committed)"
echo ""
echo "🎉 Next steps:"
echo "   1. Restart Claude Code in this workspace"
echo "   2. Test with: mcp__task-tracker__list_projects()"
echo ""
echo "💡 Tip: Each workspace/repo can have its own .mcp.local.json"
echo "   with different user credentials!"
