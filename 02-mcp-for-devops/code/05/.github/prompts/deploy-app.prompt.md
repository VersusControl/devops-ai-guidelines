---
mode: agent
description: Deploy an application manifest through the MCP server
tools: ['describe_resource', 'list_pods', 'scale_deployment']
---

Deploy the application described by **${input:manifest:path or name}** to
namespace **${input:namespace:namespace}**.

Steps:

1. Validate the manifest is a `Deployment` or `StatefulSet`.
2. Use `describe_resource` to detect whether the workload already exists.
   - If it exists, summarise the diff (replicas, image, env).
   - If it does not, list the resources that will be created.
3. **Pause and ask for confirmation** before applying.
4. After confirmation, apply the manifest using the project's CI/CD bridge
   (do NOT shell out to `kubectl apply` from inside the MCP tools — this
   prompt is read-only with respect to the cluster API).
5. Poll `list_pods` until all replicas report `Ready` or 5 minutes elapse.
