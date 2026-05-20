# Chapter 7: Advanced MCP & Kubernetes Patterns — Code

This module extends the secure server from Chapter 6 with patterns that
matter at enterprise scale.

## Packages

| Package            | Responsibility                                                          |
| ------------------ | ----------------------------------------------------------------------- |
| `pkg/cache`        | TTL + LRU resource cache shared by all read paths                       |
| `pkg/watch`        | Client-go informers fan-out into MCP notifications                      |
| `pkg/multicluster` | Loads multiple kubeconfig contexts and routes requests by cluster name  |
| `pkg/crd`          | Dynamic client + RESTMapper for arbitrary `CustomResourceDefinitions`   |
| `pkg/helm`         | Thin wrapper around the `helm` CLI for install / upgrade / list         |
| `pkg/mcp`          | Wires the above behind MCP tools and resources                          |

## Build

```bash
make deps build
./bin/k8s-mcp-advanced --clusters ./configs/clusters.yaml
```

## Demos

```bash
./scripts/demo-watch.sh         # streams Pod events through MCP notifications
./scripts/demo-multicluster.sh  # lists pods across two contexts in one call
./scripts/demo-crd.sh           # describes a Cert-Manager Certificate
```
