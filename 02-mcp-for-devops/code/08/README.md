# Chapter 8: MCP Performance & Optimization — Code

Adds production-grade performance plumbing on top of the advanced server
from Chapter 7.

## Packages

| Package          | Purpose                                                                |
| ---------------- | ---------------------------------------------------------------------- |
| `pkg/metrics`    | Prometheus counters/histograms for tool calls, k8s API, and cache      |
| `pkg/ratelimit`  | Token-bucket limiter keyed by caller identity                          |
| `pkg/pagination` | Helpers that translate MCP arguments into k8s `ListOptions` pages      |
| `pkg/profiler`   | Opt-in `net/http/pprof` endpoint                                       |
| `pkg/mcp`        | Middleware that wraps every tool handler with metrics + rate limiting  |

## Run

```bash
make build
./bin/k8s-mcp-perf --metrics-addr :9090 --pprof-addr :6060
```

Metrics are exposed at `http://localhost:9090/metrics`. pprof is at
`http://localhost:6060/debug/pprof/`.

## Benchmarks

```bash
make bench           # micro-benchmarks (cache, ratelimit, pagination)
make load            # end-to-end load test (requires hey / vegeta)
```
