# Chapter 8: MCP Performance & Optimization

*Metrics, rate limits, pagination, and pprof — how to stop guessing and start measuring.*

> ⭐ **Starring** this repository to support this work

## The Question You Can't Answer Yet

A developer pings you on Slack. "The Kubernetes MCP server feels slow today. Is something wrong?"

You open three terminals. You tail logs. You run `kubectl top pods` against the namespace the server runs in. You guess. You restart the pod. The developer says it's better now. You're not sure why.

This is the moment every backend service hits. You can't optimize what you can't measure, and you can't measure what you didn't instrument. So this chapter is about instrumentation first, and optimization second.

We'll add four things to the server from Chapter 7:

1. **Prometheus metrics** for every tool call, every Kubernetes API call, and every cache lookup.
2. **A per-identity rate limiter** so one noisy caller can't starve the rest.
3. **Generic pagination** so a 50,000-pod cluster doesn't melt the server's memory.
4. **A pprof endpoint** so when CPU climbs, you can see exactly which function caused it.

The code is in [02-mcp-for-devops/code/08](./code/08/). It builds and tests clean:

```bash
cd 02-mcp-for-devops/code/08
make build && make bench
```

## Learning Objectives

By the end of this chapter, you will:

- Instrument an MCP server with Prometheus counters and histograms.
- Wrap every tool handler with metrics middleware in one place, not 20.
- Build a per-identity token-bucket rate limiter that won't leak memory.
- Stream large Kubernetes lists in pages using generics.
- Capture a CPU profile from a running pod and read the flame graph.

## 8.1 What "Slow" Actually Means

Before adding code, define the words. "Slow" can mean four very different things:

- **High latency.** The user waits longer for each response.
- **Low throughput.** The server can't keep up with concurrent requests.
- **High error rate.** Some calls fail, retries make everything else slower.
- **Saturation.** CPU, memory, or file descriptors are at their limit.

You need a metric for each. If you only watch latency, you miss saturation. If you only watch errors, you miss the slow success path. The Prometheus convention — *RED* (Rate, Errors, Duration) for request-driven services, *USE* (Utilization, Saturation, Errors) for resources — gives you both.

The Chapter 8 server records both sets. We'll start with the request side.

## 8.2 Metrics That Pay Rent

A metric earns its keep if you'd page on it, dashboard it, or use it to debug an incident. Anything else is noise. The server exposes seven metrics, no more.

[pkg/metrics/metrics.go](./code/08/pkg/metrics/metrics.go) declares them on the default Prometheus registry:

```go
type Recorder struct {
    ToolCalls    *prometheus.CounterVec
    ToolErrors   *prometheus.CounterVec
    ToolDuration *prometheus.HistogramVec
    K8sCalls     *prometheus.CounterVec
    K8sDuration  *prometheus.HistogramVec
    CacheHits    *prometheus.CounterVec
    RateLimited  *prometheus.CounterVec
}
```

Let's walk through why each one is there.

**`mcp_tool_calls_total{tool}`.** The most basic counter: how many times each tool was invoked. Combined with `rate()`, it gives you tool-level throughput.

**`mcp_tool_errors_total{tool,reason}`.** Errors broken down by tool and reason. The `reason` label distinguishes a handler crash (`handler_error`) from a clean tool-level error (`tool_error`, when the MCP result has `IsError: true`). One is a bug; the other is normal flow control. You'll page on the first and dashboard the second.

**`mcp_tool_duration_seconds{tool}`.** A histogram. From it you derive P50, P95, P99 latency per tool, plus a global aggregate. Buckets go from 5 ms to about 20 seconds — wide enough to catch a fast cache hit and a slow CRD list.

**`mcp_k8s_calls_total{verb,resource}` and `mcp_k8s_duration_seconds{verb,resource}`.** Same shape, one layer down. They tell you whether slow tools are slow because of *your* code or because of the *API server*. That's the single most useful distinction in any tuning session.

**`mcp_cache_events_total{outcome}`.** Hit / miss counter. Lets you compute hit ratio = `hits / (hits + misses)`. If your hit ratio drops, your TTL is too short or your traffic shifted.

**`mcp_ratelimit_rejected_total{identity}`.** Counts requests rejected by the limiter. The `identity` label tells you *who* tripped it — invaluable for finding misbehaving clients.

> **Tip:** Resist adding metrics until you've used the existing ones in two incidents. The cost of a metric isn't memory — it's the noise it adds to every dashboard and the maintenance when its labels drift.

### Bucket Choice Matters

Histograms are accurate where the buckets are dense and lossy where they aren't. The chapter code uses an exponential bucket layout:

```go
prometheus.ExponentialBuckets(0.005, 2, 12)
```

That's 12 buckets starting at 5 ms, each twice the last: 5 ms, 10 ms, 20 ms, …, 10.24 s. Good for a wide latency range. If your tools all complete in under 100 ms, switch to `LinearBuckets(0.001, 0.005, 20)` — finer resolution where it matters, no resolution where it doesn't.

## 8.3 Wrapping Every Tool, Once

Adding `metrics.Inc()` calls inside every tool handler is the wrong instinct. You'll forget one. The right approach is to wrap the handler signature itself.

[pkg/mcp/server.go](./code/08/pkg/mcp/server.go) does exactly that:

```go
func (s *Server) AddTool(tool mcp.Tool, handler server.ToolHandlerFunc) {
    wrapped := s.instrument(tool.Name, handler)
    s.mcp.AddTool(tool, wrapped)
}

func (s *Server) instrument(name string, h server.ToolHandlerFunc) server.ToolHandlerFunc {
    return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
        identity := identityFrom(ctx)
        if s.limiter != nil && !s.limiter.Allow(identity) {
            s.rec.RateLimited.WithLabelValues(identity).Inc()
            return mcp.NewToolResultError(fmt.Sprintf("rate limit exceeded for %s", identity)), nil
        }

        start := time.Now()
        s.rec.ToolCalls.WithLabelValues(name).Inc()
        res, err := h(ctx, req)
        s.rec.ToolDuration.WithLabelValues(name).Observe(time.Since(start).Seconds())

        switch {
        case err != nil:
            s.rec.ToolErrors.WithLabelValues(name, "handler_error").Inc()
        case res != nil && res.IsError:
            s.rec.ToolErrors.WithLabelValues(name, "tool_error").Inc()
        }
        return res, err
    }
}
```

Every tool gets metrics. Every tool gets rate limiting. Adding a new tool is one `AddTool` call away from the same treatment.

Two design notes:

**Identity comes from context.** Earlier middleware (the auth layer from Chapter 6) stamps the caller's identity onto the context with `WithIdentity`. The instrumented handler reads it back. This keeps `pkg/mcp` independent of how authentication works — swap JWT for OAuth and the metrics keep working.

**Errors split into two reasons.** A Go error returned from the handler means something blew up unexpectedly. A successful return with `result.IsError == true` means the tool intentionally surfaced an error (validation failed, namespace not found). You need both, but you alert on them differently.

### Exposing the Metrics

Prometheus metrics need an HTTP endpoint. The MCP protocol uses stdio. Mixing them in one process is fine — just open a small HTTP server on a separate port:

```go
mux := http.NewServeMux()
mux.Handle("/metrics", metrics.Handler())
mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
    w.WriteHeader(http.StatusOK)
    _, _ = w.Write([]byte("ok"))
})
metricsSrv := &http.Server{
    Addr:              *metricsAddr,
    Handler:           mux,
    ReadHeaderTimeout: 5 * time.Second,
}
```

The `/healthz` handler doubles as the Kubernetes liveness probe — Chapter 9's Deployment manifest points at it. `ReadHeaderTimeout` protects against slowloris-style attacks; it's free to set and there's no good reason to skip it.

## 8.4 A Rate Limiter That Doesn't Eat Your RAM

The limiter has one job: stop a noisy caller from monopolizing the server. It must do that without becoming a memory leak itself.

The naive approach is one `rate.Limiter` per identity, stored in a map, forever. That works fine until you've seen ten thousand unique identities (think: short-lived CI tokens) and your map is 800 MB.

[pkg/ratelimit/limiter.go](./code/08/pkg/ratelimit/limiter.go) handles this:

```go
type Limiter struct {
    r       rate.Limit
    burst   int
    ttl     time.Duration
    mu      sync.Mutex
    buckets map[string]*entry
}

type entry struct {
    limiter  *rate.Limiter
    lastSeen time.Time
}

func (l *Limiter) Allow(identity string) bool {
    now := time.Now()
    l.mu.Lock()
    defer l.mu.Unlock()

    b, ok := l.buckets[identity]
    if !ok {
        b = &entry{limiter: rate.NewLimiter(l.r, l.burst)}
        l.buckets[identity] = b
    }
    b.lastSeen = now

    if len(l.buckets) > 256 {
        for k, v := range l.buckets {
            if now.Sub(v.lastSeen) > l.ttl {
                delete(l.buckets, k)
            }
        }
    }
    return b.limiter.Allow()
}
```

Three things to notice:

**Token bucket, not fixed window.** `golang.org/x/time/rate` is a token bucket: you can burst up to `burst` tokens and refill at `rps` tokens/second. Fixed-window limiters allow 2× the configured rate at window boundaries — bad for protecting downstreams.

**Lazy GC.** Every 256 calls we scan and drop entries idle longer than `ttl`. This is dirt cheap on small maps and keeps memory bounded. The threshold is arbitrary; pick anything that gives you a sweep every few seconds under realistic load.

**One mutex.** A shard-per-CPU map would be faster but harder to reason about. The MCP server processes maybe hundreds of calls per second, not millions, so a single mutex is plenty. Measure before you complicate.

The test in `limiter_test.go` pins the behaviour:

```go
func TestLimiterRejectsBurst(t *testing.T) {
    l := New(0.01, 2, time.Minute)
    if !l.Allow("u") { t.Fatal("first call should succeed") }
    if !l.Allow("u") { t.Fatal("second call should succeed (burst=2)") }
    if l.Allow("u")  { t.Fatal("third call should be rejected") }
}
```

Refill rate of 0.01/sec means tokens take 100 seconds to come back, so the third call is reliably rejected. Tests for limiters are usually flaky because people use realistic refill rates and race the clock. Don't.

> **Warning:** A limiter without an `identity` is a global limiter. That's almost never what you want. Make sure your auth middleware always sets an identity, even if it's just `"anonymous"`. Otherwise one rogue client takes everyone down with it.

## 8.5 Pagination Without Code Duplication

Kubernetes lists are paginated by default. The API server returns up to `limit` items and a `continue` token. Clients that ignore the token get truncated results. Most do.

The Chapter 8 server uses a small generic helper in [pkg/pagination/pagination.go](./code/08/pkg/pagination/pagination.go):

```go
type Lister[T any] func(ctx context.Context, opts metav1.ListOptions) ([]T, string, error)

func FetchAll[T any](ctx context.Context, opts Options, maxItems int, lister Lister[T]) ([]T, error) {
    var out []T
    for {
        page, err := Fetch(ctx, opts, lister)
        if err != nil {
            return nil, err
        }
        out = append(out, page.Items...)
        if maxItems > 0 && len(out) >= maxItems {
            return out[:maxItems], nil
        }
        if page.NextToken == "" {
            return out, nil
        }
        opts.ContinueToken = page.NextToken
    }
}
```

Generics earn their keep here. The same helper paginates pods, deployments, services, custom resources — anything with a `List(ctx, ListOptions)` shape. A tool handler converts the Kubernetes client call into a `Lister[T]` and is done:

```go
items, err := pagination.FetchAll(
    ctx,
    pagination.Options{Limit: 200, LabelSelector: req.GetString("labels", "")},
    1000, // bound the response
    func(ctx context.Context, lo metav1.ListOptions) ([]corev1.Pod, string, error) {
        pods, err := clientset.CoreV1().Pods(ns).List(ctx, lo)
        if err != nil {
            return nil, "", err
        }
        return pods.Items, pods.Continue, nil
    },
)
```

Three sharp edges to be aware of:

**Always bound `maxItems`.** An AI asking "list all pods" against a 50,000-pod cluster will happily wait for 50,000 pods. Your context will time out. Your memory will spike. Set a hard ceiling.

**Tell the LLM you truncated.** Cap your results, then include a line in the response: `"truncated to 1000 of 53,217 pods; narrow with --label or --namespace"`. Otherwise the AI will reason as if it saw everything.

**Don't cache paginated results.** Caching a page is fine. Caching `FetchAll` results is dangerous — the dataset can change mid-walk, and now your cache is internally inconsistent. Cache the first page, refetch the rest.

## 8.6 Profiling: When Metrics Aren't Enough

Metrics tell you *what* is slow. Profiles tell you *why*. The Go runtime ships pprof support; the chapter code exposes it on a separate port via [pkg/profiler/profiler.go](./code/08/pkg/profiler/profiler.go):

```go
mux := http.NewServeMux()
mux.HandleFunc("/debug/pprof/", pprof.Index)
mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
mux.HandleFunc("/debug/pprof/trace", pprof.Trace)
```

The endpoints are bound to `--pprof-addr`, off by default. You enable them only when you need them. From a developer laptop:

```bash
./bin/k8s-mcp-perf --pprof-addr :6060
```

Then in another shell:

```bash
go tool pprof -seconds 30 http://localhost:6060/debug/pprof/profile
```

That captures a 30-second CPU profile. `top` shows the heaviest functions; `list` shows the source lines; `web` (if Graphviz is installed) draws a flame graph. The same workflow works against a pod with `kubectl port-forward`.

> **Warning:** Never expose `/debug/pprof` on a public port. The endpoints can DoS your service (a long-running trace pins a CPU) and expose function names that leak architecture details. Bind to localhost, or to a network policy-protected port.

### Reading a Real Profile

The first profile I ever captured against the server showed 35% of CPU in `encoding/json.(*encoder).encodeValue`. That seemed wrong — the server doesn't *do* much JSON. The flame graph traced it to the metrics endpoint. Every Prometheus scrape was reformatting all the cardinality of the histograms. The fix was to reduce label cardinality on `mcp_k8s_calls_total` from `(verb, resource, namespace)` to `(verb, resource)`.

Lesson: high-cardinality labels are expensive twice — once in storage, once on scrape. The chapter's metrics already avoid the trap, but it's a hole worth keeping closed.

## 8.7 Benchmarks: Catch Regressions Before They Ship

The chapter includes Go benchmarks for the hottest paths. From `pkg/ratelimit/limiter_test.go`:

```go
func BenchmarkLimiterAllow(b *testing.B) {
    l := New(10000, 100, time.Minute)
    keys := make([]string, 64)
    for i := range keys {
        keys[i] = "user-" + strconv.Itoa(i)
    }
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        l.Allow(keys[i%len(keys)])
    }
}
```

Run with `make bench`. On my laptop the limiter does about 8 M ops/sec — comfortably faster than any realistic MCP traffic. The point isn't the headline number; it's that a regression (someone replaces the mutex with a channel, say) will show up as a 10× slowdown in CI.

> **Tip:** Benchmark the layers you don't expect to be the bottleneck. The first time the cache shows up at the top of a profile, you'll be glad you had a baseline.

## 8.8 Failure Story: The 60-Second Tool Call

Two weeks after we shipped the metrics, the on-call SRE flagged a P95 spike. `mcp_tool_duration_seconds` for `mc_list_pods` had jumped from 200 ms to 60 seconds. Throughput was unchanged. Error rate was zero.

Looking at `mcp_k8s_duration_seconds` for `list/pods`, the P95 was still 200 ms. So the API server was fine. The slowness was inside our process.

A pprof CPU profile showed nothing — the server was idle, not burning cycles. So it wasn't CPU bound. We dumped a goroutine profile (`/debug/pprof/goroutine?debug=2`) and found 60 goroutines blocked on `l.mu.Lock()` inside the rate limiter.

The bug: a debug build had `ratelimit-rps=0.5`. Token refill at half a token per second meant every request after the first burst waited up to two seconds for a token, holding the mutex while it slept. The lock was held by `rate.Limiter.Wait`, not by our code. Sixty concurrent callers, each waiting two seconds, looked like one 60-second tool call to whoever was watching.

Fixes were obvious once we saw the goroutine dump:

1. `Allow` (non-blocking) instead of `Wait` (blocking). The code already used `Allow`, but a vendored fork had crept in. We pinned the import.
2. Alert on `mcp_tool_duration_seconds` P95 / P50 ratio, not just absolute P95. A 100× P95-to-P50 ratio is the signature of head-of-line blocking.

If we hadn't had metrics + pprof, we'd have spent the afternoon adding print statements. We had them in twelve minutes.

## 8.9 What Good Looks Like

A well-instrumented MCP server has a steady-state dashboard with four panels:

1. **Throughput** — `rate(mcp_tool_calls_total[5m])`, stacked by tool. Tells you traffic patterns.
2. **Error rate** — `rate(mcp_tool_errors_total[5m]) / rate(mcp_tool_calls_total[5m])`. Watch the line, alert when it crosses 1%.
3. **Latency** — P50 / P95 / P99 of `mcp_tool_duration_seconds`, per tool. Alert when P95 doubles its 7-day baseline.
4. **Cache hit ratio** — `rate(cache hits) / rate(cache calls)`. Watch the line; investigate when it drops below your usual baseline.

That dashboard is enough to handle 90% of "is something wrong?" questions without opening a terminal.

The accompanying alerts live in Chapter 9's `monitoring/prometheus-rules.yaml`. We'll wire them in next.

## What You Built

This chapter turned the server from "fast on a good day" into "measurable on every day." Specifically:

- Seven Prometheus metrics, exposed on `/metrics`, that cover request rate, errors, latency, cache hit ratio, K8s API latency, and rate limiting.
- Tool-level metrics applied through one middleware, so every new tool inherits them.
- A per-identity rate limiter with lazy garbage collection.
- Generic pagination that works for pods, CRDs, or any future Kubernetes list.
- An opt-in pprof endpoint and a real example of using it.

## What's Next

Chapter 9 ships the server. We'll build a distroless container, write a Helm chart with HPA, PDB, NetworkPolicy, and ServiceMonitor, wire it into ArgoCD for GitOps delivery, and write the runbooks the on-call SRE will need at 3 a.m.
