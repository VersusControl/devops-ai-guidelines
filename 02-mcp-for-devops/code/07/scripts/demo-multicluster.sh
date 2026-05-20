#!/usr/bin/env bash
# Fan out a pod listing across every registered cluster.
set -euo pipefail

BIN="${BIN:-./bin/k8s-mcp-advanced}"
NAMESPACE="${NAMESPACE:-default}"

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"demo","version":"0.0.1"}}}'
CALL='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"mc_clusters","arguments":{}}}'

printf '%s\n%s\n' "$INIT" "$CALL" | "$BIN" | jq -c '.'
