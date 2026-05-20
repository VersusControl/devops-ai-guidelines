# Copilot instructions: Kubernetes MCP workspace

You are assisting an SRE/DevOps engineer who manages Kubernetes clusters
through a local MCP server (`k8s-mcp-server`). The server exposes the
following capabilities:

- **Resources**: `pods`, `services`, `deployments`, `configmaps`, `secrets`,
  `namespaces`.
- **Tools**: `list_pods`, `get_pod_logs`, `restart_pod`, `scale_deployment`,
  `describe_resource`, `delete_pod`, `create_configmap`.

## Operating rules

1. **Prefer MCP tools over `kubectl`.** When the user asks about cluster
   state, call `list_pods`, `describe_resource`, etc. Do not synthesise
   answers from memory.
2. **Always include `namespace` arguments.** Default to `default` only when
   the user did not specify one and confirm in the response.
3. **Destructive operations require explicit confirmation.** For
   `restart_pod`, `delete_pod`, or `scale_deployment` with `replicas=0`,
   restate the action and require the user to reply `yes` before invoking
   the tool. Set `confirm: true` only after explicit consent.
4. **Format output for fast scanning.** Use compact tables for lists and
   fenced YAML blocks for resource manifests.
5. **Cite tool results.** When summarising, reference the tool name and
   relevant fields (e.g. "via `list_pods` → 3/3 Ready").

## Code style for Go contributions

- Target Go 1.23+, use standard `log/slog`-style structured logging.
- Use `context.Context` as the first argument on any function that does I/O.
- Wrap external errors with `fmt.Errorf("...: %w", err)`.
- Keep MCP tool handlers thin: validate → delegate to `pkg/k8s` → format.
