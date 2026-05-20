#!/usr/bin/env bash
# Build and install the local k8s-mcp-helpers VS Code extension.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$SCRIPT_DIR/../extension"

cd "$EXT_DIR"

if [[ ! -d node_modules ]]; then
    npm install
fi

npx --yes @vscode/vsce package --out k8s-mcp-helpers.vsix
code --install-extension k8s-mcp-helpers.vsix --force
