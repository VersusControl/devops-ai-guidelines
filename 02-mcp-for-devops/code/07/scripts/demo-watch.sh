#!/usr/bin/env bash
# Stream pod events from the default cluster through the MCP server using a
# tiny JSON-RPC dialogue.
set -euo pipefail

BIN="${BIN:-./bin/k8s-mcp-advanced}"
NAMESPACE="${NAMESPACE:-default}"

if [[ ! -x "$BIN" ]]; then
    echo "build first: make build" >&2
    exit 1
fi

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"demo","version":"0.0.1"}}}'
LIST='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"mc_list_pods","arguments":{"cluster":"*","namespace":"'"$NAMESPACE"'"}}}'

printf '%s\n%s\n' "$INIT" "$LIST" | "$BIN" | jq -c '.'
