#!/usr/bin/env bash
# Smoke-test the local MCP server stdio handshake.
set -euo pipefail

SERVER_BIN="${SERVER_BIN:-$(cd "$(dirname "$0")/../../06" && pwd)/bin/k8s-mcp-server}"

if [[ ! -x "$SERVER_BIN" ]]; then
    echo "error: server binary not found at $SERVER_BIN" >&2
    echo "       run 'make build' in chapter 06 first" >&2
    exit 1
fi

echo "[1/2] initialize"
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"resources":{},"tools":{}},"clientInfo":{"name":"vscode-smoketest","version":"0.0.1"}}}'

echo "[2/2] tools/list"
LIST='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

printf '%s\n%s\n' "$INIT" "$LIST" | "$SERVER_BIN" | jq -c '.'
