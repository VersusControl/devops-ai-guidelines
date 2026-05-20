# Chapter 7: Advanced MCP & Kubernetes Patterns

*Watch APIs, caches, multi-cluster routing, CRDs, and Helm — the patterns that separate a demo from an operator-grade server.*

> ⭐ **Starring** this repository to support this work

## The Phone Call That Changed the Server

The server we built through Chapter 6 worked. It listed pods, scaled deployments, audited every call, and refused to do anything without a valid token. We shipped it to the platform team's staging cluster on a Tuesday.

By Thursday it was on fire.

The first call came from the on-call SRE: "Why is your server hitting the API server every second? You're showing up in our top-five client list." Then a developer asked, "Can it look at our ArgoCD Applications? They're CRDs." Then the platform lead asked the question that broke the design: "We have three clusters. Can the same chat answer questions about all of them?"

Each request was reasonable. Together they meant the chapter you're reading.

This chapter is about the patterns that take an MCP server from "works on my laptop" to "lives in production." We'll add five things to the server:

1. A **TTL+LRU cache** so the same question doesn't hammer the API server.
2. A **watch layer** using client-go informers, so we can stream live events instead of polling.
3. A **multi-cluster manager** so one MCP server can answer questions across a fleet.
4. A **dynamic CRD client** so we can talk to Cert-Manager, ArgoCD, or anything else without hard-coding their schemas.
5. A **Helm bridge** so the AI can install or upgrade charts on request.

The code lives in [02-mcp-for-devops/code/07](./code/07/). It builds clean with `make build`.

## Learning Objectives

By the end of this chapter, you will:

- Design a cache layer that's safe for concurrent MCP tool calls.
- Use Kubernetes informers to stream events instead of polling.
- Route a single MCP request across multiple clusters.
- Read and write any Custom Resource without compiling its types into your binary.
- Wrap the Helm CLI safely from a long-running Go process.

## 7.1 Why the Previous Server Doesn't Scale

The Chapter 6 server has three habits that won't survive production:

**It re-fetches everything, every time.** Every call to `list_pods` hits the API server. If three engineers ask "what's running in `payments`?" within five seconds, that's three identical list calls.

**It polls instead of subscribing.** When a developer asks "is the rollout done yet?", the AI calls `describe_resource` in a loop. The API server doesn't mind one client doing that. It minds twenty.

**It only knows one cluster.** The `kubeconfig` is loaded once at startup. Multi-cluster questions ("did the deploy land in staging too?") require running multiple servers.

The fix isn't to write more tools. It's to give the existing tools a better foundation. Let's start with the cheapest win.

## 7.2 A Cache You Can Trust

A cache is easy to write and easy to get wrong. Get it wrong and your AI confidently reports yesterday's pod list. The cache we want has three properties:

- **Bounded.** It can't grow forever or one big cluster will OOM the server.
- **TTL'd.** Every entry expires, so stale data has a known shelf life.
- **Concurrent-safe.** Multiple tool handlers will hit it at once.

Here's the core of [pkg/cache/store.go](./code/07/pkg/cache/store.go):

```go
type Store struct {
    mu      sync.Mutex
    maxSize int
    ttl     time.Duration
    items   map[string]*list.Element
    lru     *list.List
    now     func() time.Time
}

type entry struct {
    key       string
    value     any
    expiresAt time.Time
}

func (s *Store) Get(key string) (any, bool) {
    s.mu.Lock()
    defer s.mu.Unlock()

    elem, ok := s.items[key]
    if !ok {
        return nil, false
    }
    e := elem.Value.(*entry)
    if s.now().After(e.expiresAt) {
        s.removeLocked(elem)
        return nil, false
    }
    s.lru.MoveToFront(elem)
    return e.value, true
}
```

A few details earn their keep:

- **The `now` field is a function.** Tests inject a fake clock and assert TTL behavior without `time.Sleep`. This is a habit worth picking up — every cache, scheduler, or rate limiter should take its clock as a dependency.
- **One mutex, not a sync.Map.** `sync.Map` is tempting, but its iteration semantics are awkward and we need to evict from a linked list. A single `sync.Mutex` is easier to reason about and fast enough for an MCP server's request rate.
- **`MoveToFront` on read.** That's what makes it LRU. Without it, popular entries would still be evicted on size pressure.

The cache lives one level above the Kubernetes client. Each tool handler decides what to cache and what the key looks like. For pod listings the key is `pods:<cluster>:<namespace>`, with a 30-second TTL. Listings are cheap enough to refetch often; secrets and configmaps are not — they get longer TTLs but smaller windows of validity.

> **Warning:** Don't cache anything that the AI is about to mutate. If the next tool call is `restart_pod`, you must invalidate the pod cache for that namespace before returning, or the next `list_pods` will show the old `Running` status from before the restart.

## 7.3 From Polling to Watching

The Kubernetes API has two modes: list-and-poll, or watch. Polling is what most "quick scripts" do — call `list`, sleep, call again. Watching is what every production controller does — open a long-lived HTTP connection and receive events as they happen.

Client-go's `informers` package wraps this. An informer holds a local cache of every object of one kind, kept up-to-date by a watch stream. You register `Add`, `Update`, and `Delete` handlers, and they fire when the cluster changes. No polling. No drift.

Here's how [pkg/watch/watcher.go](./code/07/pkg/watch/watcher.go) wires it up:

```go
func (w *Watcher) attach(kind string) error {
    var informer cache.SharedIndexInformer
    switch kind {
    case "pods":
        informer = w.factory.Core().V1().Pods().Informer()
    case "deployments":
        informer = w.factory.Apps().V1().Deployments().Informer()
    // ...
    }

    _, err := informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
        AddFunc:    func(obj any) { w.publish(EventAdded, kind, obj) },
        UpdateFunc: func(_, obj any) { w.publish(EventModified, kind, obj) },
        DeleteFunc: func(obj any) { w.publish(EventDeleted, kind, obj) },
    })
    return err
}
```

Three things matter here:

**SharedInformerFactory.** Multiple parts of the server might care about pods — the cache, the live-streaming tool, future audit hooks. The factory ensures there's only one watch per kind, no matter how many subscribers attach.

**Non-blocking subscribers.** `publish` walks the subscriber list and calls each function. If one is slow, it blocks the rest. In the chapter code the subscribers just push events to channels, but if you ever do real work in a subscriber, run it in a goroutine with a bounded queue. A blocked informer eventually crashes the cache.

**Type switch in `metaOf`.** Informers return strongly-typed objects (`*corev1.Pod`, `*appsv1.Deployment`), so getting the `Namespace` and `Name` requires either a type switch or `meta.Accessor`. The code does the type switch for the common cases and falls back to the accessor.

### Bridging Informers to MCP Notifications

MCP has a notion of **server notifications** — messages the server sends without being asked. They're how a real-time MCP server tells the client, "a new pod just appeared." The MCP-Go SDK exposes these through `mcp.Server.SendNotificationToAllClients`.

The bridge is six lines:

```go
unsub := watcher.Subscribe(func(ev watch.Event) {
    s.mcpServer.SendNotificationToAllClients(
        "k8s/event",
        map[string]any{
            "type":      ev.Type,
            "kind":      ev.Kind,
            "namespace": ev.Namespace,
            "name":      ev.Name,
            "ts":        ev.Timestamp.Format(time.RFC3339),
        },
    )
})
defer unsub()
```

Now any MCP client subscribed to notifications gets a stream of cluster events. GitHub Copilot Chat doesn't yet render arbitrary notifications, but custom clients (and the in-tree chat modes from Chapter 5) can use them to drive live dashboards.

> **Note:** Watches are not free. Each informer holds a copy of every object of its kind. On a cluster with 10,000 pods, that's a few hundred megabytes of RAM. Only watch what you need, and use `informers.WithNamespace` to scope when the chapter's `pkg/watch` doesn't.

## 7.4 Multi-Cluster, Done Correctly

"Multi-cluster" sounds harder than it is. The trick is to stop thinking about kubeconfigs and start thinking about **named clusters**. Every MCP tool that touches the API takes a `cluster` argument. A registry resolves the name to a `kubernetes.Interface`. That's the whole design.

The registry file is plain YAML — see [configs/clusters.yaml](./code/07/configs/clusters.yaml):

```yaml
clusters:
  - name: dev
    context: kind-dev
  - name: staging
    kubeconfig: ~/.kube/staging.yaml
    context: staging
  - name: prod
    kubeconfig: ~/.kube/prod.yaml
    context: prod
    readOnly: true
```

The `readOnly` flag is small but important. Production clusters get marked read-only at the registry level. The server refuses any write tool when `readOnly: true`, regardless of whether the caller's RBAC would permit it. That's a second seatbelt: even an over-permissioned API key can't `delete_pod` against prod unless the registry agrees.

[pkg/multicluster/manager.go](./code/07/pkg/multicluster/manager.go) loads the file once at startup and builds a clientset per entry:

```go
func LoadFromFile(path string) (*Manager, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("read %s: %w", path, err)
    }
    var r registry
    if err := yaml.Unmarshal(data, &r); err != nil {
        return nil, fmt.Errorf("parse %s: %w", path, err)
    }
    m := &Manager{
        specs:    make(map[string]ClusterSpec, len(r.Clusters)),
        clients:  make(map[string]kubernetes.Interface, len(r.Clusters)),
        defaults: r.Clusters[0].Name,
    }
    for _, spec := range r.Clusters {
        client, err := buildClient(spec)
        if err != nil {
            return nil, fmt.Errorf("cluster %q: %w", spec.Name, err)
        }
        m.specs[spec.Name] = spec
        m.clients[spec.Name] = client
    }
    return m, nil
}
```

Two decisions to call out:

**Eager construction.** We build every client at startup. If a kubeconfig is broken, the server fails to boot. That's better than failing the first tool call at 3 a.m. when nobody knows why.

**The first cluster is the default.** Tools that omit the `cluster` argument use it. This keeps single-cluster setups simple: one cluster in the registry, no argument required.

### Fan-out in One Call

With the manager in place, fan-out is a `for` loop. The `mc_list_pods` handler in [pkg/mcp/server.go](./code/07/pkg/mcp/server.go) accepts `cluster: "*"`:

```go
targets := []string{clusterArg}
if clusterArg == "" {
    targets = []string{s.clusters.Default()}
} else if clusterArg == "*" {
    targets = s.clusters.Names()
}

for _, name := range targets {
    key := fmt.Sprintf("pods:%s:%s", name, namespace)
    if cached, ok := s.cache.Get(key); ok {
        fmt.Fprintf(&out, "[%s] (cached)\n%s\n", name, cached.(string))
        continue
    }
    c, err := s.clusters.Get(name)
    // ...
}
```

The cache key includes the cluster name, so dev and prod don't poison each other's entries. The result format brackets each cluster's output, so the AI can tell which cluster a row came from. Small detail, big difference in answer quality.

> **Tip:** Fan-out sequentially first, parallelize when you measure a problem. A `for` loop with cached entries is usually faster than three goroutines for a three-cluster fleet, and the code is half the size.

## 7.5 Talking to Resources That Didn't Exist When You Compiled

CRDs are the reason every Kubernetes shop ends up with custom Go types. ArgoCD's `Application`, Cert-Manager's `Certificate`, your own `MyAppRelease` — each has its own client library, each pulls in megabytes of dependencies.

The MCP server can dodge that entirely with the **dynamic client**. It speaks raw JSON/YAML via `unstructured.Unstructured`, and combined with the **discovery RESTMapper** it can find the right HTTP path for any `Group/Kind` the cluster knows about.

[pkg/crd/dynamic.go](./code/07/pkg/crd/dynamic.go) is short:

```go
func New(cfg *rest.Config) (*Client, error) {
    dyn, err := dynamic.NewForConfig(cfg)
    if err != nil {
        return nil, fmt.Errorf("dynamic client: %w", err)
    }
    disc, err := discovery.NewDiscoveryClientForConfig(cfg)
    if err != nil {
        return nil, fmt.Errorf("discovery client: %w", err)
    }
    mapper := restmapper.NewDeferredDiscoveryRESTMapper(memory.NewMemCacheClient(disc))
    return &Client{dyn: dyn, mapper: mapper}, nil
}

func (c *Client) List(ctx context.Context, group, kind, namespace string) ([]unstructured.Unstructured, error) {
    gvr, namespaced, err := c.resolve(group, kind)
    if err != nil {
        return nil, err
    }
    var ri dynamic.ResourceInterface = c.dyn.Resource(gvr)
    if namespaced {
        ri = c.dyn.Resource(gvr).Namespace(namespace)
    }
    list, err := ri.List(ctx, metav1.ListOptions{})
    if err != nil {
        return nil, fmt.Errorf("list %s/%s: %w", group, kind, err)
    }
    return list.Items, nil
}
```

A few things worth understanding:

**The RESTMapper does the magic.** It asks the API server "what's the resource path for `cert-manager.io/Certificate`?" and caches the answer. Without it, you'd have to hard-code `v1` versions and resource plurals — both of which can change.

**`unstructured.Unstructured` is just a `map[string]interface{}`.** You access fields with `obj.Object["status"]["conditions"]`. Ugly, but you don't need to know the schema. Perfect for an MCP tool that just needs to dump a CR to the AI.

**Cached discovery.** `memory.NewMemCacheClient` wraps the discovery client so the RESTMapper doesn't hit the API server every time you ask for a kind. It refreshes when it sees a kind it doesn't know.

### Exposing It as an MCP Tool

The `crd_list` tool in the server is twenty lines and works for every CRD on the cluster:

```go
s.mcp.AddTool(mcp.NewTool(
    "crd_list",
    mcp.WithDescription("List instances of a custom resource."),
    mcp.WithString("cluster"),
    mcp.WithString("group", mcp.Required()),
    mcp.WithString("kind", mcp.Required()),
    mcp.WithString("namespace"),
), s.handleCRDList)
```

The AI now answers questions like "Are any Cert-Manager certificates failing in `payments`?" without anyone writing a Cert-Manager-specific tool. That's the leverage of generic interfaces.

> **Warning:** Read access is safe and cheap. Write access via the dynamic client is also possible, but resist exposing it as an MCP tool. A bad LLM call that PUTs an unstructured YAML to an ArgoCD `Application` can break a whole environment. Keep CRD writes behind kind-specific tools that validate the payload.

## 7.6 Helm From a Long-Running Process

Helm is a complicated piece of software. Its Go SDK pulls in hundreds of dependencies and has historically been hard to embed safely in another binary. The pragmatic alternative — the one most platform teams actually use — is to shell out to the `helm` CLI.

That's what [pkg/helm/client.go](./code/07/pkg/helm/client.go) does:

```go
func (c *Client) Install(ctx context.Context, opts InstallOptions) (string, error) {
    args := []string{}
    if opts.Upgrade {
        args = append(args, "upgrade", "--install")
    } else {
        args = append(args, "install")
    }
    args = append(args, opts.Release, opts.Chart)
    if opts.Version != "" {
        args = append(args, "--version", opts.Version)
    }
    if opts.Namespace != "" {
        args = append(args, "--namespace", opts.Namespace, "--create-namespace")
    }
    for k, v := range opts.Values {
        args = append(args, "--set", fmt.Sprintf("%s=%s", k, v))
    }
    if opts.DryRun {
        args = append(args, "--dry-run")
    }
    args = append(args, "-o", "json")

    out, err := c.run(ctx, args...)
    if err != nil {
        return "", err
    }
    return strings.TrimSpace(string(out)), nil
}
```

The wrapper makes a few deliberate choices:

**`exec.CommandContext`, not `exec.Command`.** When the MCP tool call is cancelled (caller hangs up, timeout fires), the `helm` subprocess gets killed too. Without context-aware exec, you'd leak processes.

**Separate `stdout` and `stderr` buffers.** Helm prints progress on stderr and JSON on stdout. Mixing them produces garbage that won't unmarshal.

**`-o json` for parseability.** The AI gets structured data, not human-formatted text. Better for downstream reasoning.

### Why Not the Helm SDK?

The Helm Go SDK works, but it locks your build's Go version to whatever Helm supports, adds significant binary size, and gives you direct access to features (like `helm test`) that you probably don't want an AI invoking. Shelling out keeps the surface area small. If you need finer control later, swap in the SDK — the `Client` interface stays the same.

> **Tip:** In production, mount a versioned `helm` binary into the container instead of relying on whatever's on the host. The Chapter 9 Dockerfile shows the pattern.

## 7.7 Failure Story: The Watch That Never Stopped

The first version of `pkg/watch` had a subtle bug. The `Subscribe` method returned an unsubscribe function that nil'd the slot in `subscribers`. Here's what publishing looked like:

```go
for _, fn := range subs {
    if fn != nil {
        fn(ev)
    }
}
```

It looked fine. It passed tests. It ran cleanly in staging.

Then we deployed it to a cluster running a Helm operator that recreated 200 pods on every reconcile. The MCP server's memory climbed steadily — 200 MB, 400 MB, 800 MB. The `subscribers` slice was never shrinking. Every chat session added a subscriber. None of them ever removed it cleanly because the chat client crashed without calling unsubscribe.

The fix was two changes:

1. **Use a map keyed by a token**, not a slice. Now unsubscribe really removes the entry.
2. **Tie subscribers to a context.** When the context cancels, the subscription auto-cleans.

The lesson: any "register a callback" API needs both an explicit deregister and a fallback (context, finalizer, weak ref) for callers that don't call deregister. Trust nobody, including yourself last Tuesday.

## 7.8 Running the Advanced Server

The code in `code/07` is a single Go module:

```bash
cd 02-mcp-for-devops/code/07
make deps
make build
./bin/k8s-mcp-advanced --clusters ./configs/clusters.yaml
```

Three demo scripts exercise the new tools through stdio:

```bash
./scripts/demo-multicluster.sh   # mc_clusters
./scripts/demo-watch.sh          # mc_list_pods across all clusters
./scripts/demo-crd.sh            # crd_list for cert-manager Certificates
```

Each script pipes a tiny JSON-RPC dialogue at the server and pretty-prints the response. They're enough to convince yourself the wiring is correct before pointing GitHub Copilot Chat at it.

## What You Built

By the end of this chapter, you have a server that:

- **Caches** read-heavy tool calls with bounded memory and explicit TTLs.
- **Watches** the cluster instead of polling, and streams events as MCP notifications.
- **Routes** requests to one or many clusters from a single binary.
- **Reads** arbitrary Custom Resources without compiling their types.
- **Drives** Helm safely from a long-running process.

These are the patterns you'll see in every production MCP server, whether you write it yourself or audit somebody else's. The shapes don't change. The dependencies do.

## What's Next

Chapter 8 takes the same server and asks the next question: how fast is it, and how do we know? We'll add Prometheus metrics, a token-bucket rate limiter, generic pagination, and a pprof endpoint — so the next time someone asks "why is the MCP server slow?", you have an answer that doesn't start with "let me add some print statements."
