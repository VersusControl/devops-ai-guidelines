#!/usr/bin/env bash
# List Cert-Manager Certificates via the dynamic CRD client.
set -euo pipefail

BIN="${BIN:-./bin/k8s-mcp-advanced}"

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"demo","version":"0.0.1"}}}'
CALL='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"crd_list","arguments":{"group":"cert-manager.io","kind":"Certificate"}}}'

printf '%s\n%s\n' "$INIT" "$CALL" | "$BIN" | jq -c '.'
