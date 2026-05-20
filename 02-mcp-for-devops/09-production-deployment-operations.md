# Chapter 9: Production Deployment & Operations

*From a binary on your laptop to a service the on-call SRE trusts at 3 a.m.*

> ⭐ **Starring** this repository to support this work

## When the Server Becomes Someone Else's Problem

The first version of our MCP server was a Go binary on my laptop. The second version was a Go binary on a teammate's laptop. The third version was supposed to be a Go binary in production.

That's where it stopped being a programming problem and started being an operations problem. Someone other than me had to deploy it, monitor it, page on it, and roll it back without my help. Every shortcut I'd taken — hardcoded paths, missing health checks, no resource limits, no version pinning — became somebody else's headache.

This chapter is the work that turns a working server into a service. We'll build:

1. **A distroless container** that won't ship a shell or a package manager.
2. **A Helm chart** with HA, autoscaling, pod disruption budgets, network policies, and RBAC scoped to the principle of least privilege.
3. **GitOps delivery** through ArgoCD, with the kustomize overlays that gate each environment.
4. **CI/CD pipelines** that build, test, sign, and release the container and the chart together.
5. **Observability glue** — Prometheus alerting rules and a Grafana dashboard wired to the metrics from Chapter 8.
6. **Runbooks** that the on-call SRE can read at 3 a.m. and act on.

The code lives in [02-mcp-for-devops/code/09](./code/09/). It packages the Chapter 8 binary; nothing about the application changes here. Everything around it does.

## Learning Objectives

By the end of this chapter, you will:

- Build a minimal, secure container image for a Go server.
- Write a Helm chart that other teams can install and tune.
- Wire a Kubernetes Deployment for HA: replicas, anti-affinity, PDBs, HPAs.
- Lock down a workload with NetworkPolicy and a least-privilege ClusterRole.
- Deliver releases through GitOps without manual `kubectl apply`.
- Author an alert and a runbook that point to the same action.

## 9.1 The Container: Small, Static, Non-Root

A production container has three goals: small (fast to pull), static (no surprises at runtime), and non-root (no privilege escalation). The Chapter 9 [Dockerfile](./code/09/Dockerfile) hits all three:

```dockerfile
FROM golang:${GO_VERSION}-bookworm AS builder
WORKDIR /src
COPY ${SOURCE_DIR}/go.mod ${SOURCE_DIR}/go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY ${SOURCE_DIR}/ ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags "-s -w" -o /out/k8s-mcp-server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /out/k8s-mcp-server /app/k8s-mcp-server
USER nonroot:nonroot
EXPOSE 9090 6060
ENTRYPOINT ["/app/k8s-mcp-server"]
CMD ["--metrics-addr=:9090"]
```

Each line earns its place:

**Multi-stage with BuildKit cache mounts.** The first `RUN` only re-runs when `go.mod` or `go.sum` change. The cache mounts keep `$GOPATH/pkg/mod` and `$GOCACHE` between builds, so incremental builds take seconds.

**`CGO_ENABLED=0`.** No C linker, no glibc dependency, one static binary. This is the prerequisite for the distroless `static` image, which has no libc at all.

**`-trimpath -ldflags "-s -w"`.** Strips build paths from the binary and removes the symbol table. Smaller image, no info leaks about your developer's home directory.

**`gcr.io/distroless/static-debian12:nonroot`.** Two megabytes. No shell. No package manager. The runtime user is UID 65532. If your code has an RCE bug, the attacker has nothing to land on.

**`EXPOSE 9090 6060`.** Documents the metrics and pprof ports. It doesn't open them — Kubernetes does — but it's a hint for anyone running `docker inspect`.

Build it from the Chapter 9 directory:

```bash
cd 02-mcp-for-devops/code/09
make image            # docker build -t k8s-mcp-server:dev
docker images | grep k8s-mcp-server
```

A clean build produces a ~12 MB image. If yours is bigger, check whether `CGO_ENABLED=0` was honored.

> **Warning:** Don't be tempted to base on `alpine` "just in case you need to debug." The day you need to debug a production container is the day you regret giving the attacker a shell. Use `kubectl debug --image=busybox` for ad-hoc shells; keep the runtime image minimal.

## 9.2 The Helm Chart: One Knob Per Decision

A good Helm chart has one knob per real decision and zero knobs for everything else. The [chart in `deploy/helm/k8s-mcp-server`](./code/09/deploy/helm/k8s-mcp-server/) takes that approach.

[values.yaml](./code/09/deploy/helm/k8s-mcp-server/values.yaml) lists every tunable:

```yaml
image:
  repository: ghcr.io/devops-ai-guidelines/k8s-mcp-server
  tag: ""

replicaCount: 3

resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits:   { cpu: 1000m, memory: 512Mi }

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

pdb:
  enabled: true
  minAvailable: 2

networkPolicy:
  enabled: true
  allowedNamespaces: ["mcp-clients"]

rbac:
  create: true
  rules: [ ... ]
```

Each block maps to one decision:

- **`replicaCount` + `autoscaling`.** Static or dynamic count. The default is *both* — start at 3, scale to 10 on CPU.
- **`resources`.** Requests and limits. Requests drive scheduling; limits prevent a runaway from taking down a node.
- **`pdb`.** A PodDisruptionBudget says "never have fewer than 2 healthy pods during voluntary disruptions (node drains, rolling updates)." Without it, a careless `kubectl drain` takes the service offline.
- **`networkPolicy`.** Restrict who can call the server.
- **`rbac`.** What the server's ServiceAccount can do to the cluster.

We won't walk through every template — they're short and conventional. Let's look at the two that matter most.

### The Deployment

[templates/deployment.yaml](./code/09/deploy/helm/k8s-mcp-server/templates/deployment.yaml) is where the production discipline shows up:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "{{ .Values.service.metricsPort }}"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: server
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          livenessProbe:
            httpGet: { path: /healthz, port: metrics }
            initialDelaySeconds: 10
            periodSeconds: 20
          readinessProbe:
            httpGet: { path: /healthz, port: metrics }
            initialDelaySeconds: 3
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
```

The choices, top to bottom:

**`maxUnavailable: 0`.** Rolling updates never reduce capacity below the configured count. Combined with `maxSurge: 1`, deploys are slower but never user-visible.

**Pod and container security contexts.** Non-root user, read-only root filesystem, no capabilities, no privilege escalation. The image already runs as non-root, but the Pod spec says it out loud so the cluster's PodSecurity admission controller enforces it.

**Separate liveness and readiness probes.** Readiness has a short period — we want to add the pod to the Service quickly. Liveness has a longer period — we don't want to kill a pod for a transient hiccup. Both probe the same `/healthz` endpoint exposed in Chapter 8.

**Prometheus scrape annotations.** Two annotations and the cluster's Prometheus picks the pod up. We could also use the `ServiceMonitor` (see below) — both are wired, you pick one based on your stack.

### Pod Anti-Affinity and PDBs

Three replicas don't help if they all land on the same node and the node dies. Anti-affinity makes the scheduler spread them across nodes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: k8s-mcp-server
```

We use **preferred**, not **required**. Required anti-affinity blocks scheduling when the cluster is small, which is the wrong default. Preferred works on a 3-node cluster *and* a 30-node cluster.

The PDB pairs with the rolling update strategy:

```yaml
spec:
  minAvailable: 2
  selector:
    matchLabels:
      {{- include "k8s-mcp-server.selectorLabels" . | nindent 6 }}
```

Two healthy pods, always, even during node drains. A cluster operator running `kubectl drain` on a node hosting two replicas will be blocked until one of them re-schedules on another node first.

## 9.3 RBAC: Trust Nothing, Verify Twice

The server runs with a ServiceAccount. That ServiceAccount has a ClusterRoleBinding to a ClusterRole. The ClusterRole determines what the server can do.

The default in `values.yaml` is deliberately narrow:

```yaml
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "events", "namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments/scale"]
    verbs: ["update", "patch"]
```

Read pods, services, configmaps, events, namespaces, deployments. Write only `deployments/scale`. That's the minimum for a scaling and inspection workload. No `delete`, no `pods/exec`, no `secrets` — those need a deliberate decision and a separate role.

> **Tip:** Splitting reads and writes into two roles, with `secrets` always its own role, is the cleanest pattern. Bind only the roles each environment needs. Production binds the read-only role + scale; staging adds restart; dev adds delete. Same code, different RoleBinding.

The chart also disables `automountServiceAccountToken` on every pod that doesn't need API access. The server *does* need it, so we leave it on, but it's worth checking whenever you copy the chart.

## 9.4 Network Policy: Default Deny, Explicit Allow

By default, every pod in a Kubernetes cluster can talk to every other pod. That's the wrong default for a service that holds API server credentials.

[templates/networkpolicy.yaml](./code/09/deploy/helm/k8s-mcp-server/templates/networkpolicy.yaml) flips it:

```yaml
spec:
  podSelector:
    matchLabels:
      {{- include "k8s-mcp-server.selectorLabels" . | nindent 6 }}
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        {{- range .Values.networkPolicy.allowedNamespaces }}
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: {{ . }}
        {{- end }}
      ports:
        - protocol: TCP
          port: {{ .Values.service.metricsPort }}
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports: [{ protocol: UDP, port: 53 }]
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except: ["169.254.0.0/16"]
      ports: [{ protocol: TCP, port: 443 }]
```

Three rules:

1. **Ingress** is allowed only from listed namespaces (where the MCP clients live), only on the metrics port.
2. **Egress** to DNS is allowed (otherwise the server can't resolve the API server).
3. **Egress** to the Kubernetes API server is allowed, but the cloud metadata endpoint (`169.254.0.0/16`) is explicitly excluded — that's the IMDS, and a compromised pod could use it to steal node credentials on AWS.

> **Warning:** Network policies do nothing if your CNI doesn't enforce them. Calico, Cilium, and AWS VPC CNI with policies enabled all work. Flannel does not. Verify before you trust the manifest.

## 9.5 GitOps With ArgoCD

`kubectl apply` is fine on day one. By day fifty, you have no idea what's actually deployed where. GitOps fixes this by making the Git repo the source of truth — Kubernetes pulls from it; humans don't push to Kubernetes.

The [ArgoCD Application](./code/09/deploy/argocd/application.yaml) registers the chart with the cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://github.com/devops-ai-guidelines/devops-ai-guidelines.git
    targetRevision: main
    path: 02-mcp-for-devops/code/09/deploy/kustomize/overlays/prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

`prune: true` means Argo will delete resources that disappear from Git. `selfHeal: true` means it'll revert manual changes — the right default for production, where surprise edits are how outages start.

We point at the **kustomize overlay**, not the Helm chart, because the rendered output is easier to review in a PR. The `Makefile`'s `render` target produces the YAML the overlay consumes:

```bash
make render > deploy/kustomize/base/rendered.yaml
```

Commit that file and Argo applies it. The PR diff shows exactly what changes on the cluster. No magic, no Helm-template surprises.

> **Tip:** Some teams point Argo at the chart directly with `helm` parameters in the Application spec. It works, but PR reviews are worse — you're diffing values, not the resulting Kubernetes objects. Rendered YAML wins for everything except small charts.

## 9.6 CI/CD: Test, Build, Sign, Release

The [`.github/workflows/ci.yaml`](./code/09/.github/workflows/ci.yaml) workflow runs on every PR:

```yaml
jobs:
  go:
    strategy:
      matrix:
        module: ["03", "04", "06", "07", "08"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: "1.23" }
      - working-directory: 02-mcp-for-devops/code/${{ matrix.module }}
        run: go vet ./... && go test -race ./...
  helm:
    steps:
      - run: helm lint 02-mcp-for-devops/code/09/deploy/helm/k8s-mcp-server
  docker:
    needs: [go]
    steps:
      - uses: docker/build-push-action@v6
        with: { push: false, tags: k8s-mcp-server:ci }
```

The matrix runs every chapter's tests in parallel. The Helm job lints the chart. The Docker job builds the image to make sure the Dockerfile still works against the latest code. Nothing is pushed.

[`release.yaml`](./code/09/.github/workflows/release.yaml) runs on a Git tag:

```yaml
on:
  push:
    tags: ["v*"]
jobs:
  image:
    steps:
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/k8s-mcp-server:${{ github.ref_name }}
            ghcr.io/${{ github.repository_owner }}/k8s-mcp-server:latest
          provenance: true
          sbom: true
```

Two important details:

**`provenance: true` and `sbom: true`.** Docker Buildx emits a SLSA provenance attestation and a software bill of materials with the image. They cost nothing to enable and let downstream consumers verify what's in the image. Increasingly, compliance audits ask for them by name.

**Tags drive everything.** Cutting a release is `git tag v1.4.0 && git push --tags`. The chart job in the same workflow packages the Helm chart with matching `Chart.version` and pushes it as an OCI artifact to GHCR. One source of truth, one version, one tag.

> **Warning:** Don't release on every commit to `main`. Tag-driven releases force a deliberate cut and a CHANGELOG entry. Continuous deployment is great for the *staging* environment; production should remain a human decision.

## 9.7 Alerts That Point to Runbooks

A metric without an alert is decoration. An alert without a runbook is a 3 a.m. argument.

[monitoring/prometheus-rules.yaml](./code/09/monitoring/prometheus-rules.yaml) has four rules, each tied to an SLO:

```yaml
- alert: MCPHighToolErrorRate
  expr: |
    sum(rate(mcp_tool_errors_total[5m]))
      /
    sum(rate(mcp_tool_calls_total[5m])) > 0.01
  for: 10m
  labels: { severity: warning, slo: availability }

- alert: MCPHighToolLatency
  expr: |
    histogram_quantile(
      0.95,
      sum by (le, tool) (rate(mcp_tool_duration_seconds_bucket[5m]))
    ) > 0.5
  for: 15m
  labels: { severity: warning, slo: latency }
```

Two design choices to call out:

**`for: 10m` matters.** Without it, every transient blip pages someone. Ten minutes of sustained breach is a real problem; 30 seconds is usually a deploy in progress.

**SLO labels in the alert.** Alertmanager routing can group on `slo`, and the postmortem template asks "which SLO budget did this consume?" Tagging the alert with the answer saves an investigation step.

The full list covers availability, latency, rate-limit surges (a sign of a misbehaving client), and pod crash loops. Four alerts is plenty. Resist adding a fifth until you've handled an incident that the four didn't catch.

### The Grafana Dashboard

[grafana-dashboard.json](./code/09/monitoring/grafana-dashboard.json) is a four-panel dashboard with a tool selector. It matches the "what good looks like" set from Chapter 8:

1. Tool calls per second.
2. Error rate over five minutes.
3. P50 / P95 / P99 latency by tool.
4. Rate-limited requests by identity.

Drop it into Grafana with the standard import flow. The variables auto-populate from Prometheus once it has data.

## 9.8 Runbooks: The Code That Runs in Humans

A runbook is code for a person under pressure. It should be specific, short, and orderable.

[`docs/runbook-incident.md`](./code/09/docs/runbook-incident.md) opens with triage:

```markdown
## 1. Triage (5 minutes)
1. Open the **K8s MCP Server** Grafana dashboard.
2. Check the firing alert in alertmanager. Note:
   - alert name (`MCPHighToolErrorRate`, ...)
   - tool label
   - affected namespace / cluster
3. Confirm pods are running:
   kubectl -n mcp get pods -l app.kubernetes.io/name=k8s-mcp-server
```

Note what's *not* there: no philosophy, no architecture diagrams, no "you might want to consider…". Steps you can run, in the order to run them.

The "Stabilise" section maps symptoms to first actions:

| Symptom | First action |
| --- | --- |
| CrashLoopBackOff | `kubectl logs --previous` then `describe pod` |
| High latency | Check `mcp_k8s_duration_seconds` — likely upstream API |
| Error rate spike | `kubectl logs --tail=200` and look for repeated stack traces |
| Rate-limit surge | Find the noisy `identity` label and contact the caller |

Each row tells the on-call where to look first. Not where to look eventually — that's the diagnosis section.

The rollout runbook (`docs/runbook-rollout.md`) is shorter still:

```markdown
## Promote: dev → staging → prod

1. git tag v1.4.0 && git push --tags
2. Watch the release workflow finish.
3. Sync `k8s-mcp-server` (staging) in ArgoCD UI. Wait for Synced/Healthy.
4. Smoke test:
   kubectl -n mcp exec deploy/k8s-mcp -- /app/k8s-mcp-server --version
5. Soak in staging for ≥ 30 minutes.
6. Sync production.
```

Then a rollback section that's exactly two commands:

```bash
helm -n mcp rollback k8s-mcp 0   # 0 = previous revision
```

Operators don't need a long document. They need the right four lines.

## 9.9 Failure Story: The PDB That Wouldn't Drain

The Helm chart's PDB defaults to `minAvailable: 2`. With three replicas, that means at most one pod can be unavailable at a time. Sensible.

The first time the cluster's autoscaler tried to scale down a node hosting two of our pods, it got stuck. The autoscaler waited 15 minutes, then gave up. Node utilization stayed at 12%. The bill went up.

The bug wasn't the PDB. It was the anti-affinity. We had set **preferred** anti-affinity, not required, so two replicas had drifted onto the same node. Now draining either one violated the PDB (only one pod would remain — `minAvailable` is 2). The autoscaler couldn't make progress, and the PDB was doing its job — protecting the user from a self-inflicted outage.

Fixes were straightforward once we understood the interaction:

1. Set `topologySpreadConstraints` with `maxSkew: 1` to *encourage* spreading at scheduling time without breaking small clusters.
2. Run a weekly cron job that detects pods of the same Deployment co-located on a node and gently evicts the duplicates.
3. Add an alert on `kube_pod_status_ready{job="kube-state-metrics"}` aggregated by host — a healthy spread should never have two of our pods on the same host for more than an hour.

The lesson is general: HA primitives compose in ways the docs don't always cover. Test your PDB by actually draining a node in staging. Test your anti-affinity by counting how many of your pods land on the same node under realistic load. The first time you do this in production should not be the first time.

## 9.10 A Day in the Life

Once everything in this chapter is wired up, a normal day looks like this:

- A developer pushes a change. CI builds, tests, lints. Merge.
- A maintainer cuts a tag. The release workflow pushes a container and a chart.
- ArgoCD detects the new commit, applies the staging overlay. The dashboard goes green again after the 30-second deploy.
- The on-call gets paged exactly once that week — for a real issue. They open the dashboard, click the alert, follow the runbook, mitigate in twelve minutes.
- The postmortem documents the gap; a follow-up PR closes it.

That's the goal. Boring, predictable, debuggable. Nobody writes books about boring infrastructure, which is why so much of it is exciting in the wrong ways.

## What You Built

- A 12 MB distroless container with a static, non-root binary.
- A Helm chart with sane defaults: HA, autoscaling, PDB, anti-affinity, NetworkPolicy, restricted ClusterRole.
- A kustomize-based GitOps pipeline through ArgoCD.
- CI that runs every chapter's tests; release workflows that ship containers and charts with SBOMs.
- Four Prometheus alerts wired to a Grafana dashboard.
- Two runbooks short enough that a sleep-deprived SRE can act on them.

## The End of the Series

You've gone from the MCP protocol spec in Chapter 1 to a versioned, observable, GitOps-delivered Kubernetes operator in Chapter 9. The code is real. The patterns are the ones I'd reach for if I had to do this again tomorrow.

What's next is up to you. The patterns in this book apply to any MCP server, not just Kubernetes. The same auth middleware secures a database MCP server. The same metrics layer instruments a Terraform MCP server. The same Helm chart deploys both. The protocol is small; the engineering around it is what matters, and that's now in your hands.

Build something. Then write the runbook for it.
