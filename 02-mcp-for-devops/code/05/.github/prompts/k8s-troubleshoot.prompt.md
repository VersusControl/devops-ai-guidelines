---
mode: agent
description: Diagnose a misbehaving Kubernetes workload using MCP tools
tools: ['list_pods', 'get_pod_logs', 'describe_resource']
---

You are diagnosing **${input:resource:resource kind and name (e.g. "pod nginx")}**
in namespace **${input:namespace:namespace}**.

Follow this checklist and call MCP tools as needed:

1. Run `list_pods` filtered to the namespace and identify pods in non-Ready
   states.
2. For each suspect pod, run `describe_resource` and surface:
   - Container restart counts
   - `Events` from the last 15 minutes
   - Image pull or scheduling failures
3. Pull the last **200 lines** of logs via `get_pod_logs` for each affected
   container.
4. Produce a root-cause summary with:
   - **Symptom**
   - **Likely cause**
   - **Recommended next action** (do not execute mutations without
     confirmation)
