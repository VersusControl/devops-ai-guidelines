# Chapter 9: Production Deployment & Operations — Code

Operational scaffolding to take the MCP server from a binary on a laptop to
a hardened, observable, high-availability service.

## Layout

```
09/
├── Dockerfile                  # Multi-stage, distroless runtime
├── Makefile                    # Build, push, deploy targets
├── deploy/
│   ├── kustomize/              # base + overlays (dev / staging / prod)
│   ├── helm/k8s-mcp-server/    # Helm chart with HPA, PDB, NetworkPolicy
│   └── argocd/application.yaml # ArgoCD Application manifest
├── monitoring/
│   ├── prometheus-rules.yaml   # Alerting rules for SLOs
│   └── grafana-dashboard.json  # Drop-in dashboard
├── .github/workflows/
│   ├── ci.yaml                 # Lint + test + build
│   └── release.yaml            # Tag-driven container release + chart push
└── docs/
    ├── runbook-incident.md
    └── runbook-rollout.md
```

## Quick build & deploy (local kind cluster)

```bash
make image                              # build container locally
kind load docker-image k8s-mcp-server:dev
helm upgrade --install k8s-mcp deploy/helm/k8s-mcp-server \
    --set image.tag=dev --namespace mcp --create-namespace
kubectl -n mcp rollout status deploy/k8s-mcp
```

## SLOs covered by `monitoring/prometheus-rules.yaml`

- **Availability**: tool error rate < 1% over 30m
- **Latency**: P95 `mcp_tool_duration_seconds` < 500 ms
- **Saturation**: pod CPU usage < 80% sustained
