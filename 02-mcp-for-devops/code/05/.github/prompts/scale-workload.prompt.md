---
mode: agent
description: Safely scale a deployment up or down
tools: ['describe_resource', 'scale_deployment', 'list_pods']
---

Scale deployment **${input:deployment:deployment name}** in namespace
**${input:namespace:namespace}** to **${input:replicas:target replicas}**
replicas.

1. Call `describe_resource` for the deployment and report current desired /
   ready replicas.
2. If the change increases replicas by more than 4x, warn the user.
3. If the target is `0`, warn that the workload will be unavailable.
4. Wait for an explicit "confirm" reply before calling `scale_deployment`
   with `confirm: true`.
5. After the call, poll `list_pods` every 10s (max 6 polls) and report the
   ready/desired count until they match.
