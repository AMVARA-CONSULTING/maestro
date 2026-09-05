#!/usr/bin/env bash
# Chrome DevTools MCP over SSH to amvara2 chrome-mcp (CDP 127.0.0.1:9222).
# Used by ~/.cursor/mcp.json so lu-zero cursor-agent / Maestro /ca can call tools.
set -euo pipefail

REMOTE_SCRIPT="${CHROME_MCP_STDIO:-/home/amvara/projects/chrome-mcp/scripts/mcp-stdio.sh}"
SSH_HOST="${CHROME_MCP_SSH:-amvara2}"

# -T: no pty (keeps MCP stdio clean). LogLevel=ERROR: no banner noise on stdout.
exec ssh -T \
  -o BatchMode=yes \
  -o ConnectTimeout=15 \
  -o LogLevel=ERROR \
  "$SSH_HOST" \
  "$REMOTE_SCRIPT"
