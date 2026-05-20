# Runbook: MCP Server Incident Response

> Page received? Start the timer and work the checklist.

## 1. Triage (5 minutes)

1. Open the **K8s MCP Server** Grafana dashboard.
2. Check the firing alert in the alertmanager UI. Note:
   - alert name (`MCPHighToolErrorRate`, `MCPHighToolLatency`, ...)
   - tool label
   - affected namespace / cluster
3. Confirm pods are running:
   ```bash
   kubectl -n mcp get pods -l app.kubernetes.io/name=k8s-mcp-server
   ```

## 2. Stabilise

| Symptom                    | First action                                                          |
| -------------------------- | --------------------------------------------------------------------- |
| Pod CrashLoopBackOff       | `kubectl -n mcp logs --previous` then `kubectl describe pod`          |
| High latency               | Check `mcp_k8s_duration_seconds` — likely upstream API server         |
| Error rate spike           | `kubectl -n mcp logs -l app.kubernetes.io/name=k8s-mcp-server --tail=200` |
| Rate-limit surge           | Identify the noisy `identity` label and contact the caller           |

If users are impacted and a rollback is available, **rollback first** (see
`runbook-rollout.md`).

## 3. Diagnose

- Capture a 30s CPU profile:
  ```bash
  kubectl -n mcp port-forward deploy/k8s-mcp-k8s-mcp-server 6060:6060
  go tool pprof -seconds 30 http://localhost:6060/debug/pprof/profile
  ```
- Pull recent audit log entries (Chapter 6 audit logger output) and search
  for repeated `authorization_denied` events.
- For Kubernetes API saturation, check the cluster's `apiserver_request_total`
  metric and confirm we are not the dominant client.

## 4. Communicate

- Post a status update in `#incidents` every 15 minutes.
- When mitigated, declare resolution and schedule a postmortem.

## 5. Postmortem template

- **Timeline** (UTC)
- **Impact** (users, requests affected, SLO budget consumed)
- **Root cause**
- **Detection gap** (could we have caught this earlier?)
- **Action items** with owners and due dates
