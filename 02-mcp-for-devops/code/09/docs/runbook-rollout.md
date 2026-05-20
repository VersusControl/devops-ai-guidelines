# Runbook: Rolling Out a New MCP Server Version

## Pre-flight

- [ ] CI green on the target commit/tag.
- [ ] CHANGELOG.md entry merged.
- [ ] Chart `appVersion` bumped in `deploy/helm/k8s-mcp-server/Chart.yaml`.
- [ ] No active incidents.

## Promote: dev → staging → prod

Each environment is gated by the ArgoCD Application defined in
`deploy/argocd/application.yaml`.

```bash
git tag v1.4.0 && git push --tags     # triggers release.yaml workflow
```

Then:

1. Watch the `release` workflow finish.
2. In ArgoCD UI, sync `k8s-mcp-server` (staging) and wait for `Synced/Healthy`.
3. Smoke test:
   ```bash
   kubectl -n mcp exec deploy/k8s-mcp-k8s-mcp-server -- \
       /app/k8s-mcp-server --version
   ```
4. Soak in staging for ≥ 30 minutes. Verify dashboard SLO panels.
5. Sync the production Application.

## Rollback

```bash
helm -n mcp rollback k8s-mcp 0     # 0 = previous revision
# or via Argo: ROLLBACK in the UI
```

Then notify `#mcp-users` with the rolled-back version and the failing build.

## Post-rollout

- [ ] Update the deployment log spreadsheet (date, version, operator).
- [ ] Close the change ticket.
- [ ] If any alerts fired during the rollout, file follow-up tasks.
