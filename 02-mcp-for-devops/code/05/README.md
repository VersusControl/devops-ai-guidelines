# Chapter 5: VS Code & GitHub Copilot Integration — Code

This folder contains the configuration files, prompt assets, and a minimal
VS Code extension that wire the Kubernetes MCP server (built in Chapters 3–4
and hardened in Chapter 6) into the VS Code + GitHub Copilot development
workflow.

## What's inside

```
05/
├── .vscode/
│   ├── mcp.json             # Workspace-level MCP server registration
│   ├── settings.json        # Copilot & Go workspace settings
│   ├── tasks.json           # Tasks to build/run the MCP server
│   └── launch.json          # Debug profiles for the MCP server
├── .github/
│   ├── copilot-instructions.md   # Repo-wide Copilot instructions
│   ├── prompts/
│   │   ├── k8s-troubleshoot.prompt.md
│   │   ├── deploy-app.prompt.md
│   │   └── scale-workload.prompt.md
│   └── chatmodes/
│       └── k8s-ops.chatmode.md   # Custom chat mode tuned for k8s ops
├── extension/                # Minimal VS Code extension exposing commands
│   ├── package.json
│   ├── tsconfig.json
│   └── src/extension.ts
└── scripts/
    ├── test-mcp-connection.sh
    └── install-extension.sh
```

## Prerequisites

1. A working MCP server binary from Chapter 3/4/6 (default path:
   `../06/bin/k8s-mcp-server`). Build it first:
   ```bash
   cd ../06 && make build
   ```
2. VS Code 1.94+ with the GitHub Copilot Chat extension installed.
3. `kubectl` configured with access to your target cluster.

## Quick start

1. Open this folder in VS Code:
   ```bash
   code .
   ```
2. VS Code will detect `.vscode/mcp.json` and prompt to start the
   `k8s-mcp-server`. Accept the prompt.
3. Open Copilot Chat and switch to the **K8s Ops** chat mode.
4. Try a prompt:
   ```
   /k8s-troubleshoot pod nginx in namespace default
   ```

## Optional extension

The `extension/` folder builds a tiny extension that adds palette commands
(`MCP: List Pods`, `MCP: Scale Deployment`) which dispatch into the chat. To
package and install it locally:

```bash
cd extension
npm install
npx vsce package
./../scripts/install-extension.sh
```
